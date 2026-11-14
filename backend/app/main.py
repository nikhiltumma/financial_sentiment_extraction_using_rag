from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

from app.api.demo import router as demo_router
from app.api.live_data import router as live_data_router
from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

# The analysis and graph routes need FAISS, SentenceTransformers and a local
# model. The SignalRadar demo routes do not, so the app still boots when the
# ML stack is missing (fresh checkout, demo laptop, Ollama stopped).
try:
    from app.api.analysis import router as analysis_router
    from app.api.graph import router as graph_router
except Exception as startup_error:  # noqa: BLE001 - demo must survive this
    analysis_router = None
    graph_router = None
    print(f"[startup] ML routes disabled: {startup_error}")

app = FastAPI(
    title="Financial KG-RAG API",
    description="Multilingual Financial Sentiment Extraction using Knowledge Graphs and RAG",
    version="1.1.0"
)

app.include_router(demo_router)
app.include_router(live_data_router)

if analysis_router is not None:
    app.include_router(analysis_router)

if graph_router is not None:
    app.include_router(graph_router)


# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Financial KG-RAG API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "Financial KG-RAG",
        "ollama_configured": bool(OLLAMA_MODEL)
    }


@app.get("/ollama-status")
def ollama_status():
    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=5
        )
        response.raise_for_status()

        models = response.json().get("models", [])

        return {
            "status": "connected",
            "configured_model": OLLAMA_MODEL,
            "available_models": [
                model["name"] for model in models
            ]
        }

    except requests.RequestException as error:
        return {
            "status": "disconnected",
            "error": str(error)
        }
