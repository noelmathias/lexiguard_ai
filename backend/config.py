from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME:         str  = "Legal Intelligence System"
    VERSION:          str  = "1.0.0"
    DEBUG:            bool = True
    UPLOAD_DIR:       str  = "data/uploads"

    # LLM
    LLM_PROVIDER:         str = "ollama"
    LLM_MODEL:            str = "qwen2.5:3b"
    LLM_FALLBACK_MODEL:   str = "qwen2.5:3b"
    OLLAMA_BASE_URL:      str = "http://localhost:11434"
    LLM_TIMEOUT:          int = 90

    # CORS — comma-separated list of extra allowed origins
    # e.g. https://lexai.vercel.app,https://www.yourdomain.com
    ALLOWED_ORIGINS:      str = ""

    # Legacy
    GEMINI_API_KEY:       str = ""

    class Config:
        env_file = ".env"

settings = Settings()