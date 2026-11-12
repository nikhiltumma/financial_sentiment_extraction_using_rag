
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.kg_generator import generate_knowledge_graph


router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


class FinancialDocument(BaseModel):
    text: str = Field(min_length=10)
    document_id: Optional[str] = None
    source_name: Optional[str] = "text_input"
    language: Optional[str] = "unknown"
    sentiment_label: Optional[str] = None


class GraphGenerationRequest(BaseModel):
    documents: list[FinancialDocument] = Field(min_length=1)


@router.post("/generate")
def generate_graph(request: GraphGenerationRequest):
    try:
        documents = [
            document.model_dump()
            for document in request.documents
        ]

        return generate_knowledge_graph(documents)

    except (ValueError, RuntimeError) as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
