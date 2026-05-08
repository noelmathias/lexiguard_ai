import os
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional
from core.comparison import compare_contracts
from utils.logger import logger

router = APIRouter()

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def read_upload(file: UploadFile) -> tuple[str, str]:
    """
    Read and extract text from an uploaded PDF or TXT file.
    Returns (filename, extracted_text).
    """
    import uuid
    ext         = os.path.splitext(file.filename)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path   = os.path.join(UPLOAD_DIR, unique_name)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, f"{file.filename} exceeds 10MB limit.")

    async with aiofiles.open(file_path, "wb") as out:
        await out.write(content)

    if ext == ".pdf":
        import fitz
        doc   = fitz.open(file_path)
        pages = [
            page.get_text("text")
            for page in doc
            if page.get_text("text").strip()
        ]
        doc.close()
        if not pages:
            raise HTTPException(
                422,
                f"{file.filename} appears to be image-only. "
                "No extractable text found."
            )
        text = "\n\n".join(pages)
    else:
        text = content.decode("utf-8", errors="replace")

    if len(text.split()) < 30:
        raise HTTPException(
            422,
            f"{file.filename} is too short to analyse."
        )

    return file.filename, text


@router.post("/compare")
async def compare_documents(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    use_llm: bool = Query(
        default=True,
        description=(
            "Set false for instant static comparison (no API call). "
            "Set true for full LLM comparison (1 Gemini call)."
        )
    )
):
    """
    Upload two contracts for side-by-side comparison.

    Returns:
    - Clause-by-clause comparison table
    - Risk scores for both documents
    - Key differences
    - Which document is riskier
    - Final recommendation

    use_llm=false → static rule-based (instant, no API call)
    use_llm=true  → LLM deep comparison (1 Gemini call)
    """
    # Validate extensions
    for f in [file_a, file_b]:
        ext = os.path.splitext(f.filename)[-1].lower()
        if ext not in [".pdf", ".txt"]:
            raise HTTPException(
                400,
                f"Unsupported file type: {f.filename}. "
                "Only PDF and TXT are supported."
            )

    try:
        name_a, text_a = await read_upload(file_a)
        name_b, text_b = await read_upload(file_b)

        logger.info(
            f"[Route] Comparing '{name_a}' ({len(text_a.split())} words) "
            f"vs '{name_b}' ({len(text_b.split())} words) | LLM: {use_llm}"
        )

        result = compare_contracts(
            text_a  = text_a,
            text_b  = text_b,
            name_a  = name_a,
            name_b  = name_b,
            use_llm = use_llm
        )

        return {
            "status":          "success",
            "analysis_mode":   "llm" if use_llm else "static",
            **result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(500, f"Comparison failed: {str(e)}")


@router.post("/compare-text")
async def compare_text_documents(
    text_a: str  = Form(..., description="Full text of Document A"),
    text_b: str  = Form(..., description="Full text of Document B"),
    name_a: str  = Form(default="Document A"),
    name_b: str  = Form(default="Document B"),
    use_llm: bool = Query(default=True)
):
    """
    Compare two contracts submitted as raw text (no file upload).
    Useful for pasting contract text directly.
    """
    if len(text_a.split()) < 30:
        raise HTTPException(422, "Document A is too short to analyse.")
    if len(text_b.split()) < 30:
        raise HTTPException(422, "Document B is too short to analyse.")

    try:
        result = compare_contracts(
            text_a  = text_a,
            text_b  = text_b,
            name_a  = name_a,
            name_b  = name_b,
            use_llm = use_llm
        )
        return {
            "status":        "success",
            "analysis_mode": "llm" if use_llm else "static",
            **result
        }
    except Exception as e:
        logger.error(f"Text comparison failed: {e}")
        raise HTTPException(500, f"Comparison failed: {str(e)}")