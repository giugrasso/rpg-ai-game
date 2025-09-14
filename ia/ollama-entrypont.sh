#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve LLAMA3 model..."
ollama pull llama3.2
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid

curl http://localhost:11434/api/create -d '{
"model": "rpg-game",
"from": "llama3.2",
"system": "You are a helpful assistant that helps create RPG games"
}'