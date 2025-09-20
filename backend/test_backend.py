import asyncio
import logging
import random
from collections import defaultdict

import requests

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def main():
    print(
        "=== Test de cohérence narrative (version corrigée - actions basées sur les options IA) ==="
    )

    try:
        # 1. Initialisation
        response = requests.get(f"{BASE_URL}/config/get_model")
        if not response.json().get("model_exists"):
            print("Création du modèle game_master...")
            requests.post(f"{BASE_URL}/config/set_model")

        # Sélectionner un scénario
        scenarios = requests.get(f"{BASE_URL}/scenarios").json()
        scenario = scenarios[0]
        print(f"\nScénario: {scenario['name']}")
        print(f"Objectif: {scenario['objectives']}\n")

        # Créer une partie et ajouter un joueur
        game_response = requests.post(
            f"{BASE_URL}/games", json={"scenario_id": scenario["id"]}
        )
        game = game_response.json()
        game_id = game["id"]

        character = {
            "player_id": "player-1",
            "display_name": "Explorateur",
            "role": "Chasseur",
            "stats": {
                "force": 18,
                "intelligence": 12,
                "charisme": 14,
                "courage": 16,
                "chance": 10,
            },
            "hp": 100.0,
            "mp": 50.0,
        }
        requests.post(f"{BASE_URL}/games/{game_id}/join", json=character)

        # Variables pour le suivi
        story_elements = defaultdict(int)
        player_position = "plage"
        objectives = {
            "trouver_george": False,
            "comprendre_menace": False,
            "atteindre_heliport": False,
        }
        last_narration = ""
        last_chosen_option = None

        # 2. Premier tour - action initiale générique
        action_text = "Observer attentivement les alentours pour évaluer la situation et repérer des indices."
        print(f"\n--- Tour 1 --- Position: {player_position}")
        print(f"Action initiale: {action_text}")

        # 3. Boucle de jeu (20 tours max)
        for turn in range(1, 21):
            if turn > 1:
                print(f"\n--- Tour {turn} --- Position: {player_position}")
                # Utiliser l'action basée sur l'option choisie précédemment
                if last_chosen_option:
                    action_text = f"[Suite de l'action précédente] {last_chosen_option['description']}"
                    print(f"Action: {action_text}")
                else:
                    action_text = (
                        "Continuer l'exploration en fonction de la situation actuelle."
                    )
                    print(f"Action: {action_text}")

            # 4. Envoyer l'action et recevoir la réponse de l'IA
            response = requests.post(
                f"{BASE_URL}/games/{game_id}/action",
                json={"player_id": "player-1", "action": action_text},
            )
            response.raise_for_status()
            ai_response = response.json()

            # 5. Stocker et analyser la narration
            last_narration = ai_response["narration"].lower()
            print(f"\nNarration:\n{ai_response['narration']}")

            # Mettre à jour les éléments narratifs
            if any(
                word in last_narration
                for word in ["grognement", "rugissement", "cri", "bruit"]
            ):
                story_elements["sons_etranges"] += 1
            if any(
                word in last_narration for word in ["lueur", "lumière", "clignotement"]
            ):
                story_elements["lumiere"] += 1
            if any(word in last_narration for word in ["trace", "empreinte", "marque"]):
                story_elements["traces"] += 1
            if any(
                word in last_narration
                for word in ["george", "scientifique", "chercheur"]
            ):
                story_elements["george"] += 1
                objectives["trouver_george"] = True
            if any(
                word in last_narration for word in ["héliport", "évacuation", "centre"]
            ):
                story_elements["heliport"] += 1
                objectives["atteindre_heliport"] = True
            if any(
                word in last_narration
                for word in ["expérience", "quarantaine", "enclos", "sujet"]
            ):
                story_elements["experiences"] += 1
                objectives["comprendre_menace"] = True

            # Mettre à jour la position
            if any(
                word in last_narration
                for word in ["jungle", "forêt", "végétation", "arbres"]
            ):
                player_position = "jungle"
            elif any(
                word in last_narration
                for word in ["bâtiment", "laboratoire", "station", "porte"]
            ):
                player_position = "bâtiment"
            elif any(
                word in last_narration for word in ["plage", "rivage", "sable", "océan"]
            ):
                player_position = "plage"
            elif any(
                word in last_narration for word in ["colline", "héliport", "centre"]
            ):
                player_position = "collines centrales"

            # 6. Afficher les options proposées par l'IA
            print("\nOptions proposées par l'IA:")
            options = ai_response["options"]
            for i, opt in enumerate(options, 1):
                print(
                    f"{i}. {opt['description']} "
                    f"(SR: {opt['success_rate']:.1f}, "
                    f"ΔPV: {opt['health_point_change'] * 100:+.1f}, "
                    f"ΔMana: {opt['mana_point_change'] * 100:+.1f})"
                )

            # 7. Choisir une option aléatoirement
            chosen_option = random.choice(options)
            last_chosen_option = chosen_option  # Stocker pour le prochain tour
            print(f"\nOption choisie: {chosen_option['description']}")

            # 8. Appliquer le choix
            response = requests.post(
                f"{BASE_URL}/games/{game_id}/choose",
                json={"player_id": "player-1", "option_id": int(chosen_option["id"])},
            )
            response.raise_for_status()
            updated_game = response.json()

            # 9. Vérifier l'état du joueur
            player = next(
                p for p in updated_game["players"] if p["player_id"] == "player-1"
            )
            print(f"État: PV={player['hp']:.1f}, Mana={player['mp']:.1f}")

            # 10. Vérifier la fin de partie
            if player["hp"] <= 0:
                print("\n⚰️ Le joueur est mort! Fin de la partie.")
                break

            await asyncio.sleep(1.5)

        # 11. Résumé final
        print("\n=== Résumé de la cohérence narrative ===")
        print("Éléments narratifs mentionnés:")
        for element, count in story_elements.items():
            print(f"- {element.replace('_', ' ')}: {count} fois")

        print("\nProgression des objectifs:")
        for objective, completed in objectives.items():
            status = "✅" if completed else "❌"
            print(f"- {objective.replace('_', ' ')}: {status}")

        print(f"\nPosition finale: {player_position}")
        print(f"\nÉtat final: PV={player['hp']:.1f}, Mana={player['mp']:.1f}")

        # 12. Afficher les 3 derniers tours
        history = requests.get(f"{BASE_URL}/games/{game_id}/history").json()
        print("\n=== Derniers tours (extraits) ===")
        for i, entry in enumerate(history[-3:], 1):
            print(f"\nTour {len(history) - 3 + i}:")
            print(f"Action: {entry['action'][:60]}...")
            print(f"Narration: {entry['ai_narration'][:100]}...")
            if "chosen_option" in entry:
                print(f"Option choisie: {entry['chosen_option']}")

    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
