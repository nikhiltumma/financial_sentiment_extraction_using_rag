
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.services.preprocessing import (
    process_financial_content,
    process_uploaded_file,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


class TextAnalysisRequest(BaseModel):
    text: str
    content_type: Literal[
        "news", "social_media", "report", "document"
    ] = "news"
    language: Literal["auto", "en", "hi", "te"] = "auto"


@router.post("/text")
def analyze_text(request: TextAnalysisRequest):
    try:
        return process_financial_content(
            text=request.text,
            content_type=request.content_type,
            selected_language=request.language,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    content_type: str = Form("report"),
    language: str = Form("auto"),
):
    try:
        file_bytes = await file.read()

        # MVP upload limit: 10 MB
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File size must not exceed 10 MB."
            )

        return process_uploaded_file(
            filename=file.filename or "uploaded_file",
            file_bytes=file_bytes,
            content_type=content_type,
            selected_language=language,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
