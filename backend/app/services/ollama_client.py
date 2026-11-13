
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

        data = response.json()
        output = data.get("response", "")

        if not isinstance(output, str) or not output.strip():
            raise RuntimeError("Ollama returned an empty response.")

        return output.strip()

    except requests.Timeout as error:
        raise RuntimeError(
            f"Ollama request timed out: {error}"
        ) from error

    except requests.ConnectionError as error:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
            "Check whether the Ollama server is running."
        ) from error

    except requests.HTTPError as error:
        raise RuntimeError(
            f"Ollama returned an HTTP error: {error}"
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            f"Ollama request failed: {error}"
        ) from error

    except (ValueError, AttributeError) as error:
        raise RuntimeError(
            f"Ollama returned an invalid API response: {error}"
        ) from error


def generate_json(prompt: str) -> dict:
    """Generate, clean, and validate JSON returned by Ollama."""

    output = generate_response(prompt, json_mode=True)

    if not output:
        raise ValueError("Ollama returned an empty JSON response.")

    try:
        result = json.loads(output)

    except json.JSONDecodeError:
        # Handle JSON wrapped in Markdown code fences.
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            output.strip(),
            flags=re.IGNORECASE
        )

        try:
            result = json.loads(cleaned)

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Ollama returned invalid JSON: {output[:500]}"
            ) from error

    # The application expects a JSON object, not a list or scalar.
    if not isinstance(result, dict):
        raise ValueError(
            "Ollama returned valid JSON, but the response "
            "must be a JSON object (dictionary)."
        )

    return result
