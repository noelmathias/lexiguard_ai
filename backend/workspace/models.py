"""Workspace data models."""

"""
SQLite schema for workspace persistence.
Uses SQLAlchemy Core (no ORM) for simplicity.
"""
import sqlalchemy as sa

metadata = sa.MetaData()

workspaces = sa.Table("workspaces", metadata,
    sa.Column("id",           sa.String(36),  primary_key=True),  # UUID
    sa.Column("name",         sa.String(200), nullable=False),
    sa.Column("description",  sa.Text,        default=""),
    sa.Column("created_at",   sa.DateTime,    nullable=False),
    sa.Column("updated_at",   sa.DateTime,    nullable=False),
)

workspace_documents = sa.Table("workspace_documents", metadata,
    sa.Column("id",           sa.String(36),  primary_key=True),
    sa.Column("workspace_id", sa.String(36),  sa.ForeignKey("workspaces.id"),
              nullable=False),
    sa.Column("filename",     sa.String(500), nullable=False),
    sa.Column("file_path",    sa.String(1000),nullable=False),
    sa.Column("doc_type",     sa.String(50),  default="upload"),
    sa.Column("word_count",   sa.Integer,     default=0),
    sa.Column("chunk_count",  sa.Integer,     default=0),
    sa.Column("indexed",      sa.Boolean,     default=False),
    sa.Column("uploaded_at",  sa.DateTime,    nullable=False),
)

chat_sessions = sa.Table("chat_sessions", metadata,
    sa.Column("id",           sa.String(36),  primary_key=True),
    sa.Column("workspace_id", sa.String(36),  sa.ForeignKey("workspaces.id"),
              nullable=False),
    sa.Column("title",        sa.String(300), default="New Chat"),
    sa.Column("created_at",   sa.DateTime,    nullable=False),
    sa.Column("updated_at",   sa.DateTime,    nullable=False),
)

chat_messages = sa.Table("chat_messages", metadata,
    sa.Column("id",           sa.Integer,     primary_key=True, autoincrement=True),
    sa.Column("session_id",   sa.String(36),  sa.ForeignKey("chat_sessions.id"),
              nullable=False),
    sa.Column("role",         sa.String(20),  nullable=False),   # user|assistant
    sa.Column("content",      sa.Text,        nullable=False),
    sa.Column("intent",       sa.String(100), default=None),
    sa.Column("risk_score",   sa.Float,       default=None),
    sa.Column("confidence",   sa.Float,       default=None),
    sa.Column("created_at",   sa.DateTime,    nullable=False),
)

generated_documents = sa.Table("generated_documents", metadata,
    sa.Column("id",           sa.String(36),  primary_key=True),
    sa.Column("workspace_id", sa.String(36),  sa.ForeignKey("workspaces.id"),
              nullable=False),
    sa.Column("doc_type",     sa.String(100), nullable=False),
    sa.Column("title",        sa.String(300), nullable=False),
    sa.Column("situation",    sa.Text,        default=""),
    sa.Column("full_text",    sa.Text,        nullable=False),
    sa.Column("word_count",   sa.Integer,     default=0),
    sa.Column("created_at",   sa.DateTime,    nullable=False),
)