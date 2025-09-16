#!/bin/bash
set -euo pipefail

BASE_URL="http://localhost:8000"

echo "=== 1. Lister les scénarios disponibles ==="
curl -s "${BASE_URL}/scenarios" | jq .
SCENARIO_ID=$(curl -s "${BASE_URL}/scenarios" | jq -r '.[0].id')

echo -e "\nUtilisation du scénario: $SCENARIO_ID"

echo "=== 2. Créer une nouvelle partie ==="
GAME_ID=$(curl -s -X POST "${BASE_URL}/games" \
  -H "Content-Type: application/json" \
  -d "{\"scenario_id\":\"${SCENARIO_ID}\"}" | jq -r '.id')

echo "Partie créée avec id: $GAME_ID"

echo "=== 3. Rejoindre la partie avec un joueur (Jedi) ==="
PLAYER_ID="player-123"
CHARACTER=$(jq -n \
  --arg pid "$PLAYER_ID" \
  '{
    "player_id": $pid,
    "display_name": "Obi-Wan",
    "role": "Jedi",
    "stats": {"force": 18, "intel": 12, "charisma": 14},
    "hp": 100,
    "mp": 50
  }')

curl -s -X POST "${BASE_URL}/games/${GAME_ID}/join" \
  -H "Content-Type: application/json" \
  -d "$CHARACTER" | jq .

echo "=== 4. Envoyer une action (attaque au sabre laser) ==="
ACTION=$(jq -n \
  --arg pid "$PLAYER_ID" \
  '{
    "player_id": $pid,
    "action": "Je frappe le Stormtrooper avec mon sabre laser.",
    "meta": {"weapon": "lightsaber"}
  }')

curl -s -X POST "${BASE_URL}/games/${GAME_ID}/action" \
  -H "Content-Type: application/json" \
  -d "$ACTION" | jq .

echo "=== 5. Récupérer l’historique de la partie ==="
curl -s "${BASE_URL}/games/${GAME_ID}/history" | jq .
