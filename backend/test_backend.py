import json
from pprint import pprint

import requests

BASE_URL = "http://localhost:8000"

def main():
  try:
    print("=== 1. Lister les scénarios disponibles ===")
    response = requests.get(f"{BASE_URL}/scenarios")
    scenarios = response.json()
    pprint(json.dumps(scenarios, indent=2))

    scenario_id = scenarios[0]["id"]
    print(f"\nUtilisation du scénario: {scenario_id}")

    print("=== 2. Créer une nouvelle partie ===")
    game_data = {"scenario_id": scenario_id}
    response = requests.post(f"{BASE_URL}/games", json=game_data)
    game = response.json()
    game_id = game["id"]
    print(f"Partie créée avec id: {game_id}")

    print("=== 3. Rejoindre la partie avec un joueur (Jedi) ===")
    player_id = "player-123"
    character = {
        "player_id": player_id,
        "display_name": "James",
        "role": "Chasseur",
        "stats": {"force": 18, "intel": 12, "charisma": 14},
        "hp": 100,
        "mp": 50,
    }
    response = requests.post(f"{BASE_URL}/games/{game_id}/join", json=character)
    pprint(response.json())

    print("=== 4. Envoyer une action (Tire un coup de feu pour signaler sa présence) ===")
    action = {
        "player_id": player_id,
        "action": "Je tire un coup de feu en l'air pour signaler ma présence.",
        "meta": {"weapon": "fusil de chasse"},
    }
    response = requests.post(f"{BASE_URL}/games/{game_id}/action", json=action)
    pprint(response.json())

    print("=== 5. Récupérer l’historique de la partie ===")
    response = requests.get(f"{BASE_URL}/games/{game_id}/history")
    pprint(response.json())
  except requests.exceptions.RequestException as e:
    print(f"Erreur de requête: {e}")
  except Exception as e:
    print(f"Erreur lors des tests: {e}")

if __name__ == "__main__":
    main()
