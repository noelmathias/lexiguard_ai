from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict
from core.docgen import (
    generate_legal_document,
    format_document_response,
    build_structured_fallback,
    DOCUMENT_TYPES
)
from utils.logger import logger

router = APIRouter()


class DocumentRequest(BaseModel):
    doc_type:  str
    situation: str
    user_info: Optional[Dict] = None
    context:   Optional[str]  = ""

    model_config = {"json_schema_extra": {
        "example": {
            "doc_type":  "legal_notice",
            "situation": (
                "My landlord John Smith at 123 Main St has refused to return "
                "my security deposit of $2000 after I vacated on 1st Jan 2025."
            ),
            "user_info": None
        }
    }}


@router.get("/document-types")
def get_document_types():
    """List all supported document types with descriptions and use cases."""
    return {
        "document_types": [
            {
                "type":        k,
                "label":       v["label"],
                "description": v["description"],
                "use_cases":   v["use_cases"]
            }
            for k, v in DOCUMENT_TYPES.items()
        ]
    }


@router.post("/generate-document")
def generate_document(
    request: DocumentRequest,
    use_llm: bool = Query(
        default=True,
        description=(
            "true  = LLM-generated document (1-2 Ollama calls, better quality). "
            "false = static template (instant, no LLM, good for testing)."
        )
    )
):
    """
    Generate a structured, frontend-ready legal document.

    Supports:
    - legal_notice      → formal notice before legal proceedings
    - complaint_letter  → formal complaint to authority or organisation
    - fir_draft         → First Information Report draft for police filing

    Response includes:
    - Nested document object with sections, full_text, placeholders
    - Metadata: word_count, generation_mode, disclaimer
    - Structured sections for frontend rendering and PDF export

    use_llm=false → instant static template (zero API calls)
    use_llm=true  → LLM-generated document (1-2 Ollama calls)
    """
    if request.doc_type not in DOCUMENT_TYPES:
        raise HTTPException(
            400,
            f"Invalid doc_type '{request.doc_type}'. "
            f"Valid options: {list(DOCUMENT_TYPES.keys())}"
        )

    if len(request.situation.strip()) < 20:
        raise HTTPException(
            422,
            "Situation description too short. "
            "Please provide at least 20 characters describing your situation."
        )

    try:
        raw = generate_legal_document(
            doc_type  = request.doc_type,
            situation = request.situation,
            user_info = request.user_info,
            context   = request.context or "",
            use_llm   = use_llm
        )
        return format_document_response(raw, request.doc_type)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        return build_structured_fallback(request.doc_type)


@router.post("/generate-document/structured")
def generate_document_structured(
    doc_type: str  = Query(..., description="Document type"),
    use_llm:  bool = Query(default=True),
    fields:   Dict = None
):
    """
    Generate a document from a pre-structured fields dict.
    Use this when you already have all field values extracted.
    Skips field extraction — goes straight to generation.
    """
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(400, f"Invalid doc_type: {doc_type}")

    if not fields:
        raise HTTPException(422, "Fields dict is required.")

    try:
        from core.docgen import generate_document_llm, generate_document_static
        from datetime import datetime

        doc_text = (
            generate_document_llm(doc_type, fields)
            if use_llm
            else generate_document_static(doc_type, fields)
        )

        raw = {
            "document":        doc_text,
            "generated_date":  datetime.now().strftime("%d %B %Y"),
            "generation_mode": "llm" if use_llm else "static",
            "word_count":      len(doc_text.split()),
            "disclaimer": (
                "This document is a draft for guidance only. "
                "Review with a qualified lawyer before use."
            )
        }
        return format_document_response(raw, doc_type)

    except Exception as e:
        logger.error(f"Structured generation failed: {e}")
        return build_structured_fallback(doc_type)