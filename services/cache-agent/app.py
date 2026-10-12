"""
Recommendation warmer agent
===========================
A small Flask service that keeps movie recommendations pre-computed in Redis,
so users get fresh recommendations immediately when they log in.

How it works
------------
1. The Profiles service calls  POST /events/profile-updated  whenever a profile changes.
   The agent waits a short time (debounce) and then regenerates that profile's recommendations.
2. A sweeper regenerates any cached entry older than MAX_AGE_HOURS.
3. Clients call  GET /profiles/<id>/recommendations  and read straight from the cache.
   On a cache miss the agent asks the Inference service directly; if that also fails
   it returns an empty fallback so login is never blocked.

Redis layout
------------
  recs:{id}              hash  recommendations (JSON string), version, generated_at
  recs:index             zset  profile_id scored by generated_at     -> used by the sweeper
  recs:pending           zset  profile_id scored by "due at" time    -> debounce queue
"""
from datetime import datetime, timezone
from functools import wraps
import json
import logging
import os
import threading
import time
import urllib.request
from typing import Optional

import redis
from flask import Flask, request, jsonify
import jwt
from jwt import PyJWKClient

# ================================================================================================ #
# ========== Configuration ======================================================================= #
# ================================================================================================ #
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://inference:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

MAX_AGE_HOURS = 12            # entries older than this get refreshed
DEBOUNCE_SECONDS = 30         # wait this long after the LAST update event before refreshing
SWEEP_INTERVAL_SECONDS = 300  # how often the sweeper looks for stale entries

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("warmer")

# Flask app
app = Flask(__name__)

# Redis client
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Keycloak JWT verification configuration from environment
JWKS_URL = os.environ.get('KEYCLOAK_JWKS_URL')
if not JWKS_URL:
    raise RuntimeError("CRITICAL: KEYCLOAK_JWKS_URL environment variable is required.")
jwk_client = PyJWKClient(JWKS_URL)

KEYCLOAK_ISSUER = os.environ.get('KEYCLOAK_ISSUER')
AUDIENCE = os.environ.get('AUDIENCE')


# ================================================================================================ #
# ========== Cache Helpers ======================================================================= #
# ================================================================================================ #
# Redis key names
INDEX = "recs:index"
PENDING = "recs:pending"


def key(profile_id: str) -> str:
    """Redis key of the cached entry for a profile."""
    return f"recs:{profile_id}"


def read_entry(profile_id: str) -> Optional[dict]:
    """Return the cached entry for a profile, or None if there isn't one."""
    recommendations = r.get(key(profile_id))
    if not recommendations:
        return None
    
    return { "recommendations": json.loads(recommendations) }


# ================================================================================================ #
# ========== Background Tasks ==================================================================== #
# ================================================================================================ #
def refresh(profile_id: str) -> Optional[dict]:
    """
    Generate recommendations for a profile and cache them.

    Calls the Inference service, then stores the result.

    Returns the new entry, or None if Inference failed. On failure the existing cache
    entry is left untouched, so stale recommendations keep being served.
    """
    try:
        # Fetch recommendations from inference
        safe_id = urllib.parse.quote(profile_id, safe="")
        url = f"{INFERENCE_URL}/recommendations/generate/{safe_id}"
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.load(resp)
        except Exception:
            log.exception("Failed to fetch recommendations %s", profile_id)
            return None

        # Parse the results
        recommendations = result["recommendations"]
        generated_at = datetime.now(timezone.utc).timestamp()

        # Set new recommendations for the requested profile (replace if exist) and update timestamp
        # NOTE: All redis commands sent together (that's why we use pipe)
        pipe = r.pipeline()
        pipe.set(key(profile_id), json.dumps(recommendations))
        pipe.zadd(INDEX, {profile_id: generated_at})
        pipe.execute()

        log.info("refreshed %s (%d items)", profile_id, len(recommendations))
        return {"recommendations": recommendations, "generated_at": generated_at}
    except Exception as e:
        log.warning("refresh failed for %s: %s", profile_id, e)
        return None


def sweeper_loop() -> None:
    """
    Keep the cache fresh by refreshing entries older than MAX_AGE_HOURS.

    Every SWEEP_INTERVAL_SECONDS, ask `recs:index` for the stale profiles and refresh them
    one by one (sequential on purpose, so the sweeper can never flood Inference).
    A failed refresh stays stale and is retried on the next sweep.
    """
    while True:
        try:
            # For all profiles with recommendations cached more than MAX_AGE_HOURS ago,
            # take it from the set and refresh recommendations for it
            cutoff = time.time() - MAX_AGE_HOURS * 3600
            for pid in r.zrangebyscore(INDEX, "-inf", cutoff):
                refresh(pid)
        except Exception:
            log.exception("sweeper error")

        time.sleep(SWEEP_INTERVAL_SECONDS)


def debounce_loop() -> None:
    """
    Process profile-update events once they have been quiet for DEBOUNCE_SECONDS.

    Every second, take the profiles in `recs:pending` whose due time has passed and
    refresh them. ZREM acts as a claim: it only succeeds for one caller, so an entry is
    never processed twice.
    """
    while True:
        time.sleep(1)
        try:
            # For all updated (pending) profiles with due time in the past (score between
            # negative infinity and now), take it from the set and refresh recommendations for it
            for pid in r.zrangebyscore(PENDING, "-inf", time.time()):
                if r.zrem(PENDING, pid):  # 1 if actually removed (always succeed for single thread)
                    refresh(pid)
        except Exception:
            log.exception("debounce loop error")


# ================================================================================================ #
# ========== API ================================================================================= #
# ================================================================================================ #
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            options = {"verify_aud": bool(AUDIENCE)}

            kwargs_jwt = {
                "jwt": token,
                "key": signing_key.key,
                "algorithms": ["RS256"],
                "options": options,
            }
            if AUDIENCE:
                kwargs_jwt["audience"] = AUDIENCE
            if KEYCLOAK_ISSUER:
                kwargs_jwt["issuer"] = KEYCLOAK_ISSUER

            payload = jwt.decode(**kwargs_jwt)
            request.user_id = payload.get("sub")

            if not request.user_id:
                return jsonify({"error": "Unauthorized: Token missing sub claim"}), 401

        except Exception as e:
            log.warning("JWT Verification Failed: %s", e)
            return jsonify({"error": "Unauthorized or invalid token"}), 401

        return f(*args, **kwargs)

    return decorated

@app.post("/events/<profile_id>/profile-updated")
def profile_updated(profile_id: str):
    """
    Webhook called by the Profiles service when a profile changes.

    Does no real work: it only schedules a refresh DEBOUNCE_SECONDS from now. A repeated
    event for the same profile overwrites the due time, which restarts the wait.
    """
    # Schedule the recommendations refresh (add the due time to the set)
    r.zadd(PENDING, {profile_id: time.time() + DEBOUNCE_SECONDS})  # re-adding resets the timer

    log.info(f"scheduled recommendations refresh for profile user_id={profile_id}")
    return {"status": "queued"}, 202


@app.get("/profiles/me/recommendations")
@require_auth
def get_recommendations():
    """
    Return recommendations for a profile. The "source" field says where they came from:
      cache     -> served from Redis (the normal case)
      fallback  -> empty list so the client is never blocked
    """
    user_id = request.user_id
    entry = read_entry(user_id)
    if entry:
        return {**entry, "source": "cache"}

    return {"recommendations": [], "source": "fallback"}


# ================================================================================================ #
# ========== Main Function ======================================================================= #
# ================================================================================================ #
if __name__ == "__main__":
    r.ping()  # fail fast if Redis is down
    threading.Thread(target=debounce_loop, daemon=True).start()
    threading.Thread(target=sweeper_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))