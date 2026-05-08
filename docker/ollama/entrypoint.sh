#!/bin/sh
set -eu

# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

echo "[Ollama] Server starting..."

# Wait until the Ollama CLI can talk to the local server.
until ollama list > /dev/null 2>&1; do
    echo "[Ollama] Waiting for server to be ready..."
    sleep 2
done

echo "[Ollama] Server ready."

# Pull model if not already present
MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"

if ollama list | grep -q "$MODEL"; then
    echo "[Ollama] Model '$MODEL' already present."
else
    echo "[Ollama] Pulling model '$MODEL'..."
    ollama pull "$MODEL"
    echo "[Ollama] Model '$MODEL' ready."
fi

echo "[Ollama] Initialization complete."

# Keep Ollama process in foreground
wait $OLLAMA_PID
