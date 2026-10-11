"""
Test script
---------------------------------
This python script is used to test the AI inference model.
It sends the prompt (defined under main function) to the AI model,
processes the response (just text format) and outputs it.
"""

import os
import json
import requests


# ================================================================================================ #
# ========== Configuration ======================================================================= #
# ================================================================================================ #
MODEL_SERVER_URL = os.environ.get("MODEL_SERVER_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen2.5:0.5b")
MAX_LLM_RETRIES = int(os.environ.get("MAX_LLM_RETRIES", 2))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 500))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 60))


RECOMMENDATION_SCHEMA = {
    "type": "object",
    "required": ["recommendations"],
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "confidence"],
                "properties": {
                    "title": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


# ================================================================================================ #
# ========== Helpers ============================================================================= #
# ================================================================================================ #
def call_llm(prompt: str) -> dict:
    """
    Calls the local model via Ollama's OpenAI-compatible endpoint.
    """
    resp = requests.post(
        f"{MODEL_SERVER_URL}/v1/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "movie_recommendations",
                    "strict": True,
                    "schema": RECOMMENDATION_SCHEMA,
                },
            },
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
            "think": False,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    return _parse_json(raw_text)


def _repair_truncated_json(text: str) -> str:
    stack = []
    in_string = False
    escape = False
    last_complete_item_end = None

    for idx, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch in ("{", "["):
            stack.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
                if stack == ["{", "["]:
                    last_complete_item_end = idx
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    if not in_string and stack in (["{"], ["{", "["]):
        trimmed = text.rstrip().rstrip(",")
        closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack))
        candidate = trimmed + closing
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    if last_complete_item_end is not None:
        return text[: last_complete_item_end + 1] + "]}"

    repaired = text.rstrip()
    if in_string:
        repaired += '"'
    repaired = repaired.rstrip(",")
    closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack))
    return repaired + closing


def _parse_json(raw_text: str) -> dict:
    """
    Parses JSON from the LLM response, stripping markdown fences/preambles
    and repairing unclosed brackets if generation was truncated.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        else:
            cleaned = cleaned.lstrip("`")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    first_brace = cleaned.find("{")
    if first_brace > 0:
        cleaned = cleaned[first_brace:]

    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(cleaned)
        return parsed
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(cleaned)
        parsed, _ = decoder.raw_decode(repaired)
        return parsed


# ================================================================================================ #
# ========== Main Function ======================================================================= #
# ================================================================================================ #
if __name__ == "__main__":
    test_prompt = """Respond with ONLY a JSON object matching this exact shape, no markdown fences, no commentary:

{
  "recommendations": [
    {
      "title": "string",
      "confidence": 0.0
    }
  ]
}

Recommend 3 sci-fi movies."""
    print(call_llm(test_prompt))