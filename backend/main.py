from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from api.routes import health, query, documents, comparison
from api.routes import docgen
from core.rag import rag_system
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Legal Intelligence System...")
    rag_system.initialise()
    logger.success("RAG system ready.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title     = settings.APP_NAME,
    version   = settings.VERSION,
    docs_url  = "/docs",
    redoc_url = "/redoc",
    lifespan  = lifespan
)

# ── CORS ──────────────────────────────────────────────────────
# Explicit list covers every local Vite port + ngrok + Vercel

_BASE_ORIGINS = [
    # Vite dev server
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
    # 127.0.0.1 variants — browsers treat these as different origins
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:5173",
    # Backend itself (Swagger UI makes requests from here)
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

def _allowed_origins() -> list:
    origins = list(_BASE_ORIGINS)
    extra   = settings.ALLOWED_ORIGINS
    if extra:
        origins.extend([o.strip() for o in extra.split(",") if o.strip()])
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins      = _allowed_origins(),
    allow_origin_regex = r"https://.*\.vercel\.app",
    allow_credentials  = True,
    allow_methods      = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers      = ["*"],
    expose_headers     = ["*"],
)

app.include_router(health.router,     prefix="/api", tags=["Health"])
app.include_router(query.router,      prefix="/api", tags=["Query"])
app.include_router(documents.router,  prefix="/api", tags=["Documents"])
app.include_router(comparison.router, prefix="/api", tags=["Comparison"])
app.include_router(docgen.router,     prefix="/api", tags=["Document Generation"])


@app.get("/")
def root():
    return {
        "message":        f"{settings.APP_NAME} is running",
        "rag_status":     "ready" if rag_system.is_ready else "not ready",
        "chunks_indexed": len(rag_system.chunks)
    }