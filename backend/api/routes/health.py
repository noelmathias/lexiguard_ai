from fastapi import APIRouter
from models.schemas import HealthResponse
from config import settings
from core.llm_provider import check_ollama_health

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status=  "ok",
        version= settings.VERSION
    )

@router.get("/health/llm")
def llm_health():
    """Check Ollama server and model availability."""
    return check_ollama_health()