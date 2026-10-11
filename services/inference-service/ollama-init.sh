#!/bin/sh

# Start the server
ollama serve &

# Wait until server is up and running
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Pull the image (uses the server)
ollama pull "${INFERENCE_OLLAMA_MODEL:-qwen2.5:1.5b}"

# Avoid terminating the container
wait