"""Workspace manager."""

import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional

import sqlalchemy as sa
from .models import (
    metadata, workspaces, workspace_documents,
    chat_sessions, chat_messages, generated_documents
)
from utils.logger import logger

DB_PATH = "data/workspace.db"


def get_engine():
    engine = sa.create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)
    return engine


_engine = None

def engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


# ─────────────────────────────────────────────
# WORKSPACE CRUD
# ─────────────────────────────────────────────

def create_workspace(name: str, description: str = "") -> Dict:
    ws_id = str(uuid.uuid4())
    now   = datetime.utcnow()
    with engine().begin() as conn:
        conn.execute(workspaces.insert().values(
            id=ws_id, name=name, description=description,
            created_at=now, updated_at=now
        ))
    # Create workspace-specific upload directory
    os.makedirs(f"data/uploads/{ws_id}", exist_ok=True)
    logger.info(f"[Workspace] Created: {ws_id} — '{name}'")
    return {"id": ws_id, "name": name, "description": description}


def list_workspaces() -> List[Dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            workspaces.select().order_by(workspaces.c.updated_at.desc())
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def get_workspace(ws_id: str) -> Optional[Dict]:
    with engine().connect() as conn:
        row = conn.execute(
            workspaces.select().where(workspaces.c.id == ws_id)
        ).fetchone()
    return dict(row._mapping) if row else None


# ─────────────────────────────────────────────
# DOCUMENT MANAGEMENT
# ─────────────────────────────────────────────

def register_document(
    workspace_id: str,
    filename:     str,
    file_path:    str,
    word_count:   int = 0,
    chunk_count:  int = 0
) -> str:
    doc_id = str(uuid.uuid4())
    now    = datetime.utcnow()
    with engine().begin() as conn:
        conn.execute(workspace_documents.insert().values(
            id=doc_id, workspace_id=workspace_id,
            filename=filename, file_path=file_path,
            word_count=word_count, chunk_count=chunk_count,
            indexed=False, uploaded_at=now
        ))
    return doc_id


def get_workspace_documents(workspace_id: str) -> List[Dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            workspace_documents.select()
            .where(workspace_documents.c.workspace_id == workspace_id)
            .order_by(workspace_documents.c.uploaded_at.desc())
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def mark_document_indexed(doc_id: str, chunk_count: int):
    with engine().begin() as conn:
        conn.execute(
            workspace_documents.update()
            .where(workspace_documents.c.id == doc_id)
            .values(indexed=True, chunk_count=chunk_count)
        )


# ─────────────────────────────────────────────
# CHAT SESSION MANAGEMENT
# ─────────────────────────────────────────────

def create_chat_session(workspace_id: str, title: str = "New Chat") -> str:
    session_id = str(uuid.uuid4())
    now        = datetime.utcnow()
    with engine().begin() as conn:
        conn.execute(chat_sessions.insert().values(
            id=session_id, workspace_id=workspace_id,
            title=title, created_at=now, updated_at=now
        ))
    return session_id


def save_message(
    session_id:  str,
    role:        str,
    content:     str,
    intent:      str   = None,
    risk_score:  float = None,
    confidence:  float = None
):
    now = datetime.utcnow()
    with engine().begin() as conn:
        conn.execute(chat_messages.insert().values(
            session_id=session_id, role=role, content=content,
            intent=intent, risk_score=risk_score,
            confidence=confidence, created_at=now
        ))
        # Update session timestamp
        conn.execute(
            chat_sessions.update()
            .where(chat_sessions.c.id == session_id)
            .values(updated_at=now)
        )


def get_chat_history(session_id: str, limit: int = 20) -> List[Dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            chat_messages.select()
            .where(chat_messages.c.session_id == session_id)
            .order_by(chat_messages.c.created_at.asc())
            .limit(limit)
        ).fetchall()
    return [
        {"role": r.role, "content": r.content}
        for r in rows
    ]


def get_chat_sessions(workspace_id: str) -> List[Dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            chat_sessions.select()
            .where(chat_sessions.c.workspace_id == workspace_id)
            .order_by(chat_sessions.c.updated_at.desc())
        ).fetchall()
    return [dict(r._mapping) for r in rows]


# ─────────────────────────────────────────────
# GENERATED DOCUMENTS
# ─────────────────────────────────────────────

def save_generated_document(
    workspace_id: str,
    doc_type:     str,
    title:        str,
    situation:    str,
    full_text:    str
) -> str:
    doc_id = str(uuid.uuid4())
    now    = datetime.utcnow()
    with engine().begin() as conn:
        conn.execute(generated_documents.insert().values(
            id=doc_id, workspace_id=workspace_id,
            doc_type=doc_type, title=title, situation=situation,
            full_text=full_text, word_count=len(full_text.split()),
            created_at=now
        ))
    return doc_id


def get_generated_documents(workspace_id: str) -> List[Dict]:
    with engine().connect() as conn:
        rows = conn.execute(
            generated_documents.select()
            .where(generated_documents.c.workspace_id == workspace_id)
            .order_by(generated_documents.c.created_at.desc())
        ).fetchall()
    return [dict(r._mapping) for r in rows]