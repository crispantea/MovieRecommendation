"""Create random Keycloak users and measure recommendation latency and throughput."""

import argparse
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

import requests


def succeeded(sample):
    status = sample[2]
    return isinstance(status, int) and 200 <= status < 300


def timed_request(session, step, method, url, **kwargs):
    started = time.perf_counter()
    try:
        response = session.request(method, url, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = None
        status = response.status_code
    except requests.RequestException:
        body, status = None, "ERR"
    return (step, time.perf_counter() - started, status), body


def get_admin_token(args):
    response = requests.post(
        f"{args.keycloak_url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": args.admin_user,
            "password": args.admin_password,
        },
        timeout=args.timeout,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_users(args, count):
    admin_token = get_admin_token(args)
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = []
    for _ in range(count):
        username = f"load-{secrets.token_hex(6)}"
        password = secrets.token_urlsafe(24) + "aA1!"
        user = {
            "username": username,
            "email": f"{username}@load.test",
            "firstName": "Load",
            "lastName": "Tester",
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        }
        response = requests.post(
            f"{args.keycloak_url}/admin/realms/{args.realm}/users",
            headers=headers,
            json=user,
            timeout=args.timeout,
        )
        if response.status_code != 201:
            raise RuntimeError(
                f"Could not create test user ({response.status_code}): {response.text}"
            )
        users.append((user['email'], password))
    return users


def login(args, session, username, password):
    return timed_request(
        session,
        "login",
        "POST",
        f"{args.keycloak_url}/realms/{args.realm}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": args.client_id,
            "username": username,
            "password": password,
        },
        timeout=args.timeout,
    )


def virtual_user(args, credentials):
    username, password = credentials
    with requests.Session() as session:
        _, token_response = login(args, session, username, password)
        token = token_response.get("access_token") if isinstance(token_response, dict) else None
        if not token:
            return None

        session.headers["Authorization"] = f"Bearer {token}"
        recommendation_sample, _ = timed_request(
            session,
            "recommendations",
            "POST",
            f"{args.inference_url}/recommendations/generate",
            json={"message": args.prompt},
            timeout=args.timeout,
        )
        return recommendation_sample


def run_level(args, clients, users):
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=clients) as pool:
        results = list(pool.map(lambda user: virtual_user(args, user), users[:clients]))
    elapsed = time.perf_counter() - started
    successful = [sample for sample in results if sample and succeeded(sample)]
    throughput = len(successful) / elapsed
    avg_latency = (
        sum(sample[1] for sample in successful) / len(successful)
        if successful
        else None
    )

    latency_text = f"{avg_latency:.2f} s" if avg_latency is not None else "n/a"
    print(f"{clients} clients | throughput: {throughput:.2f} recommendations/s | average latency: {latency_text}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clients", nargs="+", type=int, default=[1, 2, 4])
    parser.add_argument("--prompt", default="Recommend a science fiction movie for tonight.")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--keycloak-url", default=os.getenv("KEYCLOAK_URL", "http://localhost:8080"))
    parser.add_argument("--realm", default=os.getenv("KEYCLOAK_APP_REALM", "agi-project"))
    parser.add_argument("--client-id", default=os.getenv("KEYCLOAK_APP_CLIENT_ID", "agi-web"))
    parser.add_argument("--inference-url", default=os.getenv("INFERENCE_API_URL", "http://localhost:8000"))
    args = parser.parse_args()

    if any(value < 1 for value in args.clients) or args.timeout <= 0:
        parser.error("clients and timeout must be positive")
    args.admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    args.admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    if not args.admin_password:
        parser.error("source .env and .env.secrets first to set KEYCLOAK_ADMIN_PASSWORD")

    for name in ("keycloak_url", "inference_url"):
        setattr(args, name, getattr(args, name).rstrip("/"))

    users = create_users(args, max(args.clients))
    for clients in args.clients:
        run_level(args, clients, users)


if __name__ == "__main__":
    main()