#!/bin/sh

# Start the server
ollama serve &

# Wait until server is up and running
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Pull the image (uses the server)
ollama pull llama3.1:8b

# Avoid terminating the container
wait