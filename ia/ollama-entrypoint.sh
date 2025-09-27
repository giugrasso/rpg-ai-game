#!/bin/bash
# Encodez bien le fichier en LF et non en CRLF !
# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

# retreive model from backend\.env OLLAMA_MODEL variable
echo "🔴 Retrieve DEEPSEEK-R1 model..."
ollama pull deepseek-r1:14b
# ollama pull huihui_ai/deepseek-r1-abliterated:14b
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid

