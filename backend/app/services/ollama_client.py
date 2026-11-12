
import requests
import json
import re

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def generate_response(prompt: str, json_mode: bool = False) -> str:
    """Send a prompt to the configured local Ollama model."""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=180
        )
        response.raise_for_status()

        return response.json().get("response", "")

    except requests.RequestException as error:
        raise RuntimeError(f"Ollama request failed: {error}")


def generate_json(prompt: str) -> dict:
    """Generate and parse JSON from Ollama."""

    output = generate_response(prompt, json_mode=True)

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Handle models that wrap JSON in Markdown fences.
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            output.strip(),
            flags=re.IGNORECASE
        )
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Ollama returned invalid JSON: {output[:500]}"
            ) from error
