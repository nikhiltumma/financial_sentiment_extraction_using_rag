
from unittest.mock import patch
from app.services.ollama_client import generate_json


def test_valid_json():
    with patch(
        "app.services.ollama_client.generate_response",
        return_value='{"sentiment": "Bullish", "label": 1}'
    ):
        result = generate_json("Test prompt")

        assert result["sentiment"] == "Bullish"
        assert result["label"] == 1

    print("PASS: Valid JSON")


def test_markdown_json():
    with patch(
        "app.services.ollama_client.generate_response",
        return_value='```json\n{"sentiment": "Neutral", "label": 2}\n```'
    ):
        result = generate_json("Test prompt")

        assert result["sentiment"] == "Neutral"

    print("PASS: Markdown-wrapped JSON")


def test_invalid_json():
    with patch(
        "app.services.ollama_client.generate_response",
        return_value='{"sentiment": "Bullish",'
    ):
        try:
            generate_json("Test prompt")
            raise AssertionError("Invalid JSON was accepted")
        except ValueError as error:
            assert "invalid JSON" in str(error)
    
    print("PASS: Invalid JSON rejected")


def test_json_array():
    with patch(
        "app.services.ollama_client.generate_response",
        return_value='[{"sentiment": "Bullish"}]'
    ):
        try:
            generate_json("Test prompt")
            raise AssertionError("JSON array was accepted")
        except ValueError as error:
            assert "JSON object" in str(error)

    print("PASS: JSON array rejected")


if __name__ == "__main__":
    test_valid_json()
    test_markdown_json()
    test_invalid_json()
    test_json_array()

    print("\nAll tests completed successfully!")
