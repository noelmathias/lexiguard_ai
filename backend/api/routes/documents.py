import os
import uuid
import aiofiles

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Query
)

from typing import Optional

from core.input_handler import process_input
from core.contract import analyse_contract
from core.rag import rag_system

from workspace.manager import (
    register_document,
    mark_document_indexed
)

from workspace.ws_index import WorkspaceIndexCache

from utils.logger import logger

router = APIRouter()

# Workspace memory cache
ws_cache = WorkspaceIndexCache(
    lambda: rag_system.embedder
)

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

async def save_upload(file: UploadFile) -> tuple[str, bytes]:
    """Save uploaded file. Returns (path, content_bytes)."""

    ext         = os.path.splitext(file.filename)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path   = os.path.join(UPLOAD_DIR, unique_name)

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            "File too large. Max 10MB allowed."
        )

    async with aiofiles.open(file_path, "wb") as out:
        await out.write(content)

    logger.info(
        f"Saved upload: {file_path} "
        f"({len(content)} bytes)"
    )

    return file_path, content


def extract_text_from_upload(
    file_path: str,
    content: bytes,
    ext: str
) -> str:
    """Extract text from PDF or TXT upload."""

    if ext == ".pdf":

        import fitz

        doc = fitz.open(file_path)

        pages = [
            page.get_text("text")
            for page in doc
            if page.get_text("text").strip()
        ]

        doc.close()

        if not pages:
            raise HTTPException(
                422,
                "PDF appears to be image-only. "
                "No extractable text found."
            )

        return "\n\n".join(pages)

    return content.decode(
        "utf-8",
        errors="replace"
    )


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@router.post("/upload")
async def upload_document(
    workspace_id: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    query: Optional[str] = Form(
        default="Analyze this document."
    )
):
    """
    Upload a PDF or text file for general processing.
    Returns extracted text preview and chunk count.
    """

    ext = os.path.splitext(file.filename)[-1].lower()

    if ext not in [".pdf", ".txt"]:
        raise HTTPException(
            400,
            "Only PDF and TXT files are supported."
        )

    file_path, content = await save_upload(file)

    try:

        if ext == ".pdf":

            processed = process_input(
                text=query,
                file_path=file_path
            )

        else:

            raw_text = content.decode(
                "utf-8",
                errors="replace"
            )

            processed = process_input(
                text=raw_text
            )

        # ─────────────────────────────────────
        # WORKSPACE MEMORY INTEGRATION
        # ─────────────────────────────────────

        if workspace_id:

            doc_id = register_document(
                workspace_id = workspace_id,
                filename     = file.filename,
                file_path    = file_path,
                word_count   = len(processed["content"].split()),
                chunk_count  = len(processed["chunks"])
            )

            ws_index = ws_cache.get(workspace_id)

            ws_chunks = []

            for idx, chunk in enumerate(
                processed["chunks"]
            ):

                ws_chunks.append({
                    "chunk_id": f"{doc_id}_chunk_{idx}",
                    "title": file.filename,
                    "text": chunk,
                    "source": "workspace",
                    "document_id": doc_id
                })

            ws_index.add_document(
                chunks = ws_chunks,
                doc_id = doc_id
            )

            mark_document_indexed(
                doc_id = doc_id,
                chunk_count = len(ws_chunks)
            )

            ws_cache.invalidate(workspace_id)

            logger.info(
                f"[Workspace] Indexed upload into workspace "
                f"{workspace_id}"
            )

        return {
            "filename":    file.filename,
            "input_type":  processed["input_type"],
            "word_count":  len(processed["content"].split()),
            "chunk_count": len(processed["chunks"]),
            "preview":     processed["content"][:500],
            "status":      "success"
        }

    except Exception as e:

        logger.error(
            f"Upload processing failed: {e}"
        )

        raise HTTPException(
            500,
            f"Processing failed: {str(e)}"
        )


@router.post("/analyze-contract")
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    use_llm: bool = Query(
        default=True,
        description=(
            "Set false to use static analysis only "
            "(no API call)"
        )
    )
):
    """
    Upload a contract PDF or TXT for full clause extraction
    and risk analysis.

    use_llm=false → static rule-based analysis
    use_llm=true  → full LLM analysis
    """

    ext = os.path.splitext(file.filename)[-1].lower()

    if ext not in [".pdf", ".txt"]:
        raise HTTPException(
            400,
            "Only PDF and TXT contracts are supported."
        )

    file_path, content = await save_upload(file)

    try:

        contract_text = extract_text_from_upload(
            file_path,
            content,
            ext
        )

        if len(contract_text.split()) < 30:

            raise HTTPException(
                422,
                "Document too short to analyse. "
                "Please upload a complete contract."
            )

        analysis = analyse_contract(
            contract_text = contract_text,
            filename      = file.filename,
            use_llm       = use_llm
        )

        return {
            "filename":      file.filename,
            "word_count":    len(contract_text.split()),
            "analysis_mode": (
                "llm" if use_llm else "static"
            ),
            "status":        "success",
            **analysis
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.error(
            f"Contract analysis failed: {e}"
        )

        raise HTTPException(
            500,
            f"Analysis failed: {str(e)}"
        )


@router.post("/upload-compare")
async def upload_for_comparison(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...)
):
    """
    Upload two documents for comparison.
    Returns extracted text from both.
    """

    path_a, content_a = await save_upload(file_a)
    path_b, content_b = await save_upload(file_b)

    ext_a = os.path.splitext(file_a.filename)[-1].lower()
    ext_b = os.path.splitext(file_b.filename)[-1].lower()

    try:

        text_a = extract_text_from_upload(
            path_a,
            content_a,
            ext_a
        )

        text_b = extract_text_from_upload(
            path_b,
            content_b,
            ext_b
        )

        from core.input_handler import process_comparison_input

        norm_a, norm_b = process_comparison_input(
            text_a,
            text_b
        )

        return {
            "file_a":      file_a.filename,
            "file_b":      file_b.filename,
            "input_type":  "comparison",
            "doc_a_words": len(norm_a.split()),
            "doc_b_words": len(norm_b.split()),
            "preview_a":   norm_a[:300],
            "preview_b":   norm_b[:300],
            "status":      "success"
        }

    except Exception as e:

        logger.error(
            f"Comparison upload failed: {e}"
        )

        raise HTTPException(
            500,
            f"Processing failed: {str(e)}"
        )
