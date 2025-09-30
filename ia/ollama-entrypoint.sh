#!/bin/bash
# Encodez bien le fichier en LF et non en CRLF !
# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

model_name="gpt-oss:20b"

# retreive model from backend\.env OLLAMA_MODEL variable
echo "🔴 Retrieve $model_name model..."
# ollama pull deepseek-r1:14b
ollama pull $model_name
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid

