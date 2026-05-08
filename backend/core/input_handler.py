import os
import re
import fitz  # PyMuPDF
import aiofiles
from typing import Dict, List, Optional, Tuple
from enum import Enum
from utils.logger import logger


# ─────────────────────────────────────────────
# INPUT TYPE ENUM
# ─────────────────────────────────────────────

class InputType(str, Enum):
    PLAIN_TEXT    = "plain_text"
    CHAT          = "chat"
    PDF           = "pdf"
    RAW_DOCUMENT  = "raw_document"
    COMPARISON    = "comparison"


# ─────────────────────────────────────────────
# INPUT DETECTOR
# ─────────────────────────────────────────────

def detect_input_type(
    text: Optional[str] = None,
    chat_history: Optional[List[dict]] = None,
    file_path: Optional[str] = None,
    doc_b: Optional[str] = None
) -> InputType:
    """
    Automatically detect what kind of input we received.
    Priority order: comparison > pdf > chat > raw_document > plain_text
    """
    # Comparison: two documents provided
    if doc_b is not None:
        return InputType.COMPARISON

    # PDF file uploaded
    if file_path and file_path.lower().endswith(".pdf"):
        return InputType.PDF

    # Multi-turn chat: history has prior messages
    if chat_history and len(chat_history) > 0:
        return InputType.CHAT

    # Raw document: long text without a specific question pattern
    if text and len(text.split()) > 200:
        return InputType.RAW_DOCUMENT

    # Default: plain text query
    return InputType.PLAIN_TEXT


# ─────────────────────────────────────────────
# PDF EXTRACTOR
# ─────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract and clean text from a PDF file using PyMuPDF.
    Handles multi-page PDFs, skips empty pages.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info(f"Extracting text from PDF: {file_path}")
    doc = fitz.open(file_path)
    pages_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages_text.append(f"[Page {page_num + 1}]\n{text.strip()}")

    doc.close()

    if not pages_text:
        raise ValueError("PDF appears to be empty or image-only (no extractable text).")

    full_text = "\n\n".join(pages_text)
    logger.info(f"Extracted {len(pages_text)} pages, {len(full_text.split())} words.")
    return full_text


# ─────────────────────────────────────────────
# TEXT NORMALIZER
# ─────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Normalize raw text input:
    - Remove excess whitespace
    - Fix broken line breaks
    - Strip non-printable characters
    - Preserve legal punctuation
    """
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    # Fix hyphenated line breaks (common in PDFs)
    text = re.sub(r'-\n', '', text)
    # Collapse multiple newlines into two
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Strip
    text = text.strip()
    return text


# ─────────────────────────────────────────────
# CHAT HISTORY FLATTENER
# ─────────────────────────────────────────────

def flatten_chat_history(
    chat_history: List[dict],
    current_query: str
) -> str:
    """
    Flatten multi-turn chat history into a single context string
    for retrieval. Format: role: message
    """
    lines = []
    for turn in chat_history:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")

    lines.append(f"User: {current_query}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# CHUNKER (for uploaded content)
# ─────────────────────────────────────────────

def chunk_text_for_query(
    text: str,
    chunk_size: int = 150,
    overlap: int = 30
) -> List[str]:
    """
    Chunk uploaded/extracted text for retrieval.
    Same strategy as Phase 1 chunker.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


# ─────────────────────────────────────────────
# COMPARISON PROCESSOR
# ─────────────────────────────────────────────

def process_comparison_input(
    doc_a: str,
    doc_b: str,
    is_pdf_a: bool = False,
    is_pdf_b: bool = False
) -> Tuple[str, str]:
    """
    Process two documents for comparison.
    Each can be raw text or a PDF file path.
    Returns normalized text for both.
    """
    # Process Document A
    if is_pdf_a:
        text_a = extract_text_from_pdf(doc_a)
    else:
        text_a = doc_a

    # Process Document B
    if is_pdf_b:
        text_b = extract_text_from_pdf(doc_b)
    else:
        text_b = doc_b

    text_a = normalize_text(text_a)
    text_b = normalize_text(text_b)

    logger.info(f"Comparison — Doc A: {len(text_a.split())} words | Doc B: {len(text_b.split())} words")
    return text_a, text_b


# ─────────────────────────────────────────────
# MASTER INPUT PROCESSOR
# ─────────────────────────────────────────────

def process_input(
    text: Optional[str] = None,
    chat_history: Optional[List[dict]] = None,
    file_path: Optional[str] = None,
    doc_b: Optional[str] = None,
    doc_b_is_pdf: bool = False
) -> Dict:
    """
    Master function — detects input type and returns
    a unified ProcessedInput dict for downstream use.

    Returns:
    {
        "input_type": InputType,
        "query": str,           # clean query for retrieval
        "content": str,         # full normalized text
        "chunks": List[str],    # chunked content (for uploads)
        "doc_a": str,           # comparison only
        "doc_b": str,           # comparison only
        "chat_history": list    # original history
    }
    """
    input_type = detect_input_type(text, chat_history, file_path, doc_b)
    logger.info(f"Detected input type: {input_type}")

    result = {
        "input_type": input_type,
        "query": "",
        "content": "",
        "chunks": [],
        "doc_a": None,
        "doc_b": None,
        "chat_history": chat_history or []
    }

    # ── PLAIN TEXT ──
    if input_type == InputType.PLAIN_TEXT:
        normalized = normalize_text(text or "")
        result["query"] = normalized
        result["content"] = normalized

    # ── CHAT ──
    elif input_type == InputType.CHAT:
        flat = flatten_chat_history(chat_history or [], text or "")
        result["query"] = text or ""
        result["content"] = flat

    # ── PDF ──
    elif input_type == InputType.PDF:
        extracted = extract_text_from_pdf(file_path)
        normalized = normalize_text(extracted)
        chunks = chunk_text_for_query(normalized)
        result["query"] = text or "Analyze this document."
        result["content"] = normalized
        result["chunks"] = chunks

    # ── RAW DOCUMENT ──
    elif input_type == InputType.RAW_DOCUMENT:
        normalized = normalize_text(text or "")
        chunks = chunk_text_for_query(normalized)
        result["query"] = text[:300]  # use first 300 chars as query
        result["content"] = normalized
        result["chunks"] = chunks

    # ── COMPARISON ──
    elif input_type == InputType.COMPARISON:
        is_pdf_a = file_path is not None and file_path.lower().endswith(".pdf")
        text_a = file_path if is_pdf_a else (text or "")
        text_a_norm, text_b_norm = process_comparison_input(
            text_a, doc_b or "",
            is_pdf_a=is_pdf_a,
            is_pdf_b=doc_b_is_pdf
        )
        result["query"] = "Compare these two documents."
        result["content"] = f"DOCUMENT A:\n{text_a_norm}\n\nDOCUMENT B:\n{text_b_norm}"
        result["doc_a"] = text_a_norm
        result["doc_b"] = text_b_norm
        result["chunks"] = chunk_text_for_query(text_a_norm) + \
                           chunk_text_for_query(text_b_norm)

    logger.info(
        f"Processed — words: {len(result['content'].split())} | "
        f"chunks: {len(result['chunks'])}"
    )
    return result