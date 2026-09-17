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
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3.1:8b")
MAX_LLM_RETRIES = int(os.environ.get("MAX_LLM_RETRIES", 2))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 60))


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
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    return _parse_json(raw_text)
    
def _parse_json(raw_text: str) -> dict:
    """
    Removes unnecessary text commonly appended by the AI model:
    - Spaces
    - ```
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("json", "", 1)
    return json.loads(cleaned)


# ================================================================================================ #
# ========== Main Function ======================================================================= #
# ================================================================================================ #
if __name__ == "__main__":
    test_prompt = """Respond with ONLY a JSON object matching this exact shape, no markdown fences, no commentary:

{
  "recommendations": [
    {
      "title": "string",
      "year": 0000,
      "genres": ["string"],
      "reason": "one sentence",
      "confidence": 0.0
    }
  ]
}

Recommend 3 sci-fi movies."""
    print(call_llm(test_prompt))