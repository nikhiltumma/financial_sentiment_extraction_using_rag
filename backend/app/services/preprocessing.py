
import re
import csv
import io
from pathlib import Path
from datetime import datetime, timezone

import fitz  # PyMuPDF
import pandas as pd
from docx import Document
from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "bn": "Bengali",
    "ta": "Tamil",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "ur": "Urdu",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ar": "Arabic",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}


def clean_text(text: str) -> str:
    """Clean text without removing Hindi or Telugu characters."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> dict:
    """Detect English, Hindi or Telugu."""
    if not text or len(text.strip()) < 20:
        return {
            "code": "unknown",
            "name": "Unknown",
            "supported": False,
        }

    try:
        code = detect(text)
    except LangDetectException:
        code = "unknown"

    return {
        "code": code,
        "name": SUPPORTED_LANGUAGES.get(code, "Other"),
        "supported": code in SUPPORTED_LANGUAGES,
    }


def extract_pdf(file_bytes: bytes) -> str:
    text_parts = []

    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text_parts.append(page.get_text())

    return "\n".join(text_parts)


def extract_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))

    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs)


def extract_csv(file_bytes: bytes) -> str:
    # utf-8-sig handles common Excel-exported CSV files.
    content = file_bytes.decode("utf-8-sig", errors="replace")
    dataframe = pd.read_csv(io.StringIO(content))

    # Convert rows into readable text for later processing.
    return dataframe.fillna("").astype(str).to_string(index=False)


def extract_file_text(filename: str, file_bytes: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if extension == ".pdf":
        return extract_pdf(file_bytes)

    if extension == ".docx":
        return extract_docx(file_bytes)

    if extension == ".txt":
        return file_bytes.decode("utf-8-sig", errors="replace")

    if extension == ".csv":
        return extract_csv(file_bytes)

    raise ValueError("Unable to process this file.")


def process_financial_content(
    text: str,
    content_type: str = "news",
    source_name: str = "text_input",
    selected_language: str = "auto",
) -> dict:
    """Prepare financial content and preserve its original text."""

    if not text or not text.strip():
        raise ValueError("Input text is empty.")

    original_text = text.strip()
    cleaned_text = clean_text(original_text)

    detected = detect_language(cleaned_text)

    if selected_language != "auto":
        if selected_language not in SUPPORTED_LANGUAGES:
            raise ValueError("Language must be en, hi, te or auto.")

        language = {
            "code": selected_language,
            "name": SUPPORTED_LANGUAGES[selected_language],
            "supported": True,
            "selection": "user_selected",
        }
    else:
        language = {
            **detected,
            "selection": "automatic",
        }

    return {
        "document_id": f"doc_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "original_text": original_text,
        "cleaned_text": cleaned_text,
        "language": language,
        "content_type": content_type,
        "source_name": source_name,
        "character_count": len(cleaned_text),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def process_uploaded_file(
    filename: str,
    file_bytes: bytes,
    content_type: str = "report",
    selected_language: str = "auto",
) -> dict:
    extracted_text = extract_file_text(filename, file_bytes)

    return process_financial_content(
        text=extracted_text,
        content_type=content_type,
        source_name=filename,
        selected_language=selected_language,
    )
