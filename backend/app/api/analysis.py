
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app.services.kg_retriever import KGRetriever

from app.services.preprocessing import (
    process_financial_content,
    process_uploaded_file,
)

from app.services.kg_reasoner import (
    check_evidence_sufficiency,
    classify_financial_sentiment,
    classify_with_fallback,
    answer_financial_question
)


router = APIRouter(prefix="/analysis", tags=["Analysis"])


class TextAnalysisRequest(BaseModel):
    text: str
    content_type: Literal[
        "news", "social_media", "report", "document"
    ] = "news"

    language: Literal[
        "auto", "en", "hi", "te"
    ] = "auto"


@router.post("/text")
def analyze_text(request: TextAnalysisRequest):
    try:
        return process_financial_content(
            text=request.text,
            content_type=request.content_type,
            selected_language=request.language,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


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

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


class FinancialQueryRequest(BaseModel):
    query: str = Field(min_length=5)
    top_k: int = Field(default=5, ge=1, le=20)


# Reuse the embedding model and FAISS index
retriever = KGRetriever()


@router.post("/query")
def analyze_financial_query(request: FinancialQueryRequest):

    try:
        # 1. Retrieve relevant graph evidence
        initial_evidence = retriever.search(
            query=request.query,
            top_k=request.top_k,
            company="ABC Technologies"
        )

        if not initial_evidence:
            raise HTTPException(
                status_code=404,
                detail="No relevant knowledge graph evidence found."
            )

        # 2. Expand evidence using one-hop relationships
        expanded_evidence = retriever.expand_one_hop(
            initial_evidence
        )

        # 3. Check evidence sufficiency
        sufficiency = check_evidence_sufficiency(
            request.query,
            expanded_evidence
        )

        answer_result = None

        # 4. Generate a direct answer and classify sentiment
        if sufficiency["sufficient"]:

            # Direct question answering
            answer_result = answer_financial_question(
                request.query,
                expanded_evidence
            )

            # Evidence-based sentiment classification
            sentiment_result = classify_financial_sentiment(
                request.query,
                expanded_evidence
            )

            classification_source = "knowledge_graph"

        else:

            # Fallback classification when evidence is insufficient
            sentiment_result = classify_with_fallback(
                request.query,
                expanded_evidence
            )

            classification_source = "llm_fallback"

        # 5. Return the complete response
        return {
            "status": "success",
            "query": request.query,

            "classification_source": classification_source,

            "evidence_sufficiency": sufficiency,

            "answer": answer_result,

            "sentiment": sentiment_result,

            "initial_evidence_count": len(initial_evidence),

            "expanded_evidence_count": len(expanded_evidence),

            "retrieved_evidence": [
                {
                    "text": item["text"],
                    "similarity_score": item.get("similarity_score"),
                    "graph_id": item.get("graph_id"),
                    "source": item.get("source"),
                    "target": item.get("target"),
                    "sentiment_label": item.get("sentiment_label"),
                    "expansion_type": item.get(
                        "expansion_type", "initial"
                    )
                }
                for item in expanded_evidence
            ]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
