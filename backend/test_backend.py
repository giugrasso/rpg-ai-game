import asyncio
import logging
import random
from pprint import pprint

import requests

# Configuration du logging pour le débogage
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

async def main():
    print("=== Démarrage du test du backend RPG-AI-Game ===")

    # 1. Vérifier/créer le modèle Ollama
    print("\n=== 1. Vérification du modèle Ollama ===")
    try:
        response = requests.get(f"{BASE_URL}/config/get_model")
        pprint(response.json())
        if not response.json().get("model_exists"):
            print("Création du modèle game_master...")
            response = requests.post(f"{BASE_URL}/config/set_model")
            pprint(response.json())
    except Exception as e:
        print(f"Erreur lors de la vérification/création du modèle: {e}")
        return

    # 2. Lister les scénarios disponibles
    print("\n=== 2. Liste des scénarios ===")
    try:
        response = requests.get(f"{BASE_URL}/scenarios")
        scenarios = response.json()
        pprint(scenarios)
        if not scenarios:
            print("Aucun scénario disponible !")
            return
        scenario_id = scenarios[0]["id"]
        print(f"\nScénario sélectionné: {scenario_id}")
    except Exception as e:
        print(f"Erreur lors de la liste des scénarios: {e}")
        return

    # 3. Créer une nouvelle partie
    print("\n=== 3. Création d'une nouvelle partie ===")
    try:
        game_data = {"scenario_id": scenario_id}
        response = requests.post(f"{BASE_URL}/games", json=game_data)
        game = response.json()
        game_id = game["id"]
        print(f"Partie créée avec ID: {game_id}")
    except Exception as e:
        print(f"Erreur lors de la création de la partie: {e}")
        return

    # 4. Rejoindre la partie avec un joueur (Chasseur)
    print("\n=== 4. Ajout d'un joueur (Chasseur) ===")
    try:
        player_id = "player-1"
        character = {
            "player_id": player_id,
            "display_name": "Aventurier",
            "role": "Chasseur",
            "stats": {"force": 18, "intelligence": 12, "charisme": 14, "courage": 16, "chance": 10},
            "hp": 100.0,
            "mp": 50.0,
        }
        response = requests.post(f"{BASE_URL}/games/{game_id}/join", json=character)
        pprint(response.json())
    except Exception as e:
        print(f"Erreur lors de l'ajout du joueur: {e}")
        return

    # 5. Boucle de jeu (10 tours max)
    print("\n=== 5. Début de la partie (10 tours max) ===")
    actions = [
        "Regarder autour de moi pour repérer des indices.",
        "Avancer prudemment vers la lumière au loin.",
        "Écouter attentivement les bruits de la jungle.",
        "Chercher de la nourriture ou des fournitures.",
        "Examiner les bâtiments abandonnés à proximité.",
        "Allumer une torche pour explorer les alentours.",
        "Suivre les traces de pas dans la boue.",
        "Crier 'Hello?' pour voir si quelqu'un répond.",
        "Inspecter le sol pour trouver des objets utiles.",
        "Se reposer un moment pour récupérer des forces.",
    ]

    for turn in range(1, 11):
        print(f"\n--- Tour {turn} ---")

        try:
            # Choix aléatoire d'une action
            action_text = random.choice(actions)
            print(f"\nAction choisie: {action_text}")

            # Envoyer l'action au backend
            action_data = {"player_id": player_id, "action": action_text}
            response = requests.post(f"{BASE_URL}/games/{game_id}/action", json=action_data)
            response.raise_for_status()  # Vérifie les erreurs HTTP
            ai_response = response.json()
            print("\nRéponse de l'IA:")
            pprint(ai_response)

            print("\nOptions disponibles:")
            for opt in ai_response["options"]:
                print(f"  - ID: {opt['id']} (type: {type(opt['id'])}), Description: {opt['description']}")

            # Vérifier s'il y a des options
            if not ai_response.get("options"):
                print("Aucune option disponible. Fin de la partie.")
                break

            # Choix aléatoire d'une option
            chosen_option = random.choice(ai_response["options"])
            print(f"\nOption choisie aléatoirement (ID: {chosen_option['id']}): {chosen_option['description']}")
            print(f"Taux de réussite: {chosen_option['success_rate']:.1f}")
            hp_impact = chosen_option['health_point_change'] * 100
            mp_impact = chosen_option['mana_point_change'] * 100
            print(f"Impact PV: {hp_impact:.1f} (multiplicateur: {chosen_option['health_point_change']:.2f})")
            print(f"Impact Mana: {mp_impact:.1f} (multiplicateur: {chosen_option['mana_point_change']:.2f})")

            # Envoyer le choix au backend
            print(f"Type de l'ID de l'option: {type(chosen_option['id'])}")
            print(f"Valeur de l'ID: {chosen_option['id']}")

            choose_data = {"player_id": player_id, "option_id": int(chosen_option["id"])}
            response = requests.post(f"{BASE_URL}/games/{game_id}/choose", json=choose_data)
            response.raise_for_status()  # Vérifie les erreurs HTTP
            updated_game = response.json()

            # Trouver le joueur mis à jour
            player = next(p for p in updated_game["players"] if p["player_id"] == player_id)
            print("\nÉtat du joueur après le choix:")
            print(f"PV: {player['hp']:.1f}, Mana: {player['mp']:.1f}")

            # Vérifier si le joueur est mort
            if player['hp'] <= 0:
                print("⚰️ Le joueur est mort! Fin de la partie.")
                break

            # Attendre 2 secondes pour simuler un temps de réflexion
            await asyncio.sleep(2)

        except requests.exceptions.HTTPError as err:
            print(f"Erreur HTTP: {err}")
            print(f"Réponse: {response.text if 'response' in locals() else 'N/A'}")
            break
        except Exception as e:
            print(f"Erreur inattendue: {e}")
            break

    # 6. Afficher l'historique de la partie
    print("\n=== 6. Historique de la partie ===")
    try:
        response = requests.get(f"{BASE_URL}/games/{game_id}/history")
        history = response.json()
        pprint(history)
    except Exception as e:
        print(f"Erreur lors de la récupération de l'historique: {e}")

    print("\n=== Fin du test ===")

if __name__ == "__main__":
    asyncio.run(main())
