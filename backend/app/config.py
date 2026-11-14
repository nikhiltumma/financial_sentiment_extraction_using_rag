import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)
