FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --retries 10 -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

COPY . .

RUN mkdir -p \
    data/uploads \
    data/index \
    data/processed \
    data/raw \
    data/workspace_chunks \
    logs \
    evaluation/reports

RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "--access-log"]
