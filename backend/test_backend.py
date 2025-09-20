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
    print("=== Test de cohérence narrative avec gestion améliorée des réponses IA ===")

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
        current_action = (
            "Observer attentivement les alentours pour évaluer la situation."
        )

        # 2. Boucle de jeu (20 tours max)
        for turn in range(1, 21):
            print(f"\n--- Tour {turn} --- Position: {player_position}")

            try:
                # Envoyer l'action et recevoir la réponse de l'IA
                response = requests.post(
                    f"{BASE_URL}/games/{game_id}/action",
                    json={"player_id": "player-1", "action": current_action},
                )

                if response.status_code != 200:
                    print(f"Erreur {response.status_code}: {response.text}")
                    # En cas d'erreur, utiliser une action générique pour le prochain tour
                    current_action = (
                        "Reporter son attention sur les alentours immédiats."
                    )
                    await asyncio.sleep(1)
                    continue

                ai_response = response.json()

                # Vérifier que la réponse contient bien une narration
                if "narration" not in ai_response:
                    print(
                        "Réponse IA invalide - utilisation d'une narration par défaut"
                    )
                    ai_response = {
                        "narration": "L'IA a rencontré un problème technique. Vous continuez votre exploration avec prudence.",
                        "options": [
                            {
                                "id": 1,
                                "description": "Continuer l'exploration",
                                "success_rate": 0.7,
                                "health_point_change": 0.0,
                                "mana_point_change": 0.0,
                                "related_stat": "chance",
                            }
                        ],
                    }

                # Stocker et analyser la narration
                last_narration = ai_response["narration"].lower()
                print(f"\nNarration:\n{ai_response['narration']}")

                # Mettre à jour les éléments narratifs
                if any(
                    word in last_narration
                    for word in ["grognement", "rugissement", "cri", "bruit"]
                ):
                    story_elements["sons_etranges"] += 1
                if any(
                    word in last_narration
                    for word in ["lueur", "lumière", "clignotement"]
                ):
                    story_elements["lumiere"] += 1
                if any(
                    word in last_narration for word in ["trace", "empreinte", "marque"]
                ):
                    story_elements["traces"] += 1
                if any(
                    word in last_narration
                    for word in ["george", "scientifique", "chercheur"]
                ):
                    story_elements["george"] += 1
                    objectives["trouver_george"] = True
                if any(
                    word in last_narration
                    for word in ["héliport", "évacuation", "centre"]
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
                    word in last_narration
                    for word in ["plage", "rivage", "sable", "océan"]
                ):
                    player_position = "plage"
                elif any(
                    word in last_narration for word in ["colline", "héliport", "centre"]
                ):
                    player_position = "collines centrales"

                # Afficher les options proposées par l'IA
                print("\nOptions proposées par l'IA:")
                options = ai_response["options"]

                # Vérifier que les options sont valides
                if not options or not isinstance(options, list):
                    print("Options IA invalides - utilisation d'options par défaut")
                    options = [
                        {
                            "id": 1,
                            "description": "Continuer l'exploration avec prudence",
                            "success_rate": 0.7,
                            "health_point_change": 0.0,
                            "mana_point_change": 0.0,
                            "related_stat": "chance",
                        }
                    ]

                for i, opt in enumerate(options, 1):
                    stat_value = character["stats"].get(
                        opt.get("related_stat", "chance"), 10
                    )
                    adjusted_success = opt.get("success_rate", 0.5) * (stat_value / 10)
                    print(
                        f"{i}. {opt.get('description', 'Option non disponible')} "
                        f"(SR: {opt.get('success_rate', 0.5):.1f} → {adjusted_success:.2f} avec "
                        f"{opt.get('related_stat', 'chance')}={stat_value}, "
                        f"ΔPV: {opt.get('health_point_change', 0.0) * 100:+.1f}, "
                        f"ΔMana: {opt.get('mana_point_change', 0.0) * 100:+.1f})"
                    )

                # Choisir une option aléatoirement
                if not options:
                    print(
                        "Aucune option valide disponible - utilisation d'une option par défaut"
                    )
                    chosen_option = {
                        "id": 1,
                        "description": "Continuer prudemment",
                        "success_rate": 0.7,
                        "health_point_change": 0.0,
                        "mana_point_change": 0.0,
                        "related_stat": "chance",
                    }
                else:
                    chosen_option = random.choice(options)

                print(
                    f"\nOption choisie: {chosen_option.get('description', 'Option par défaut')}"
                )

                # Calculer le succès ajusté
                stat_value = character["stats"].get(
                    chosen_option.get("related_stat", "chance"), 10
                )
                adjusted_success = chosen_option.get("success_rate", 0.5) * (
                    stat_value / 10
                )
                print(
                    f"Taux de réussite de base: {chosen_option.get('success_rate', 0.5):.1f}"
                )
                print(
                    f"Taux ajusté avec {chosen_option.get('related_stat', 'chance')}={stat_value}: {adjusted_success:.2f}"
                )

                # Appliquer le choix
                try:
                    response = requests.post(
                        f"{BASE_URL}/games/{game_id}/choose",
                        json={
                            "player_id": "player-1",
                            "option_id": int(chosen_option.get("id", 1)),
                        },
                    )

                    if response.status_code != 200:
                        print(f"Erreur lors du choix: {response.text}")
                        # Continuer avec une action générique
                        current_action = (
                            "Reporter son attention sur les alentours immédiats."
                        )
                        await asyncio.sleep(1)
                        continue

                    updated_game = response.json()

                    # Vérifier le résultat du jet de dé
                    dice_roll = requests.get(
                        f"{BASE_URL}/games/{game_id}/last_roll"
                    ).json()
                    if dice_roll:
                        print(
                            f"\nRésultat du jet de dé: {dice_roll.get('narration', 'Jet non disponible')}"
                        )

                    # Vérifier l'état du joueur
                    player = next(
                        p
                        for p in updated_game["players"]
                        if p["player_id"] == "player-1"
                    )
                    print(f"État: PV={player['hp']:.1f}, Mana={player['mp']:.1f}")

                    # Préparer l'action pour le prochain tour
                    current_action = f"[Suite] {chosen_option.get('description', "Continuer l'exploration")}"

                    # Vérifier la fin de partie
                    if player["hp"] <= 0:
                        print("\n⚰️ Le joueur est mort! Fin de la partie.")
                        break

                except Exception as e:
                    print(f"Erreur lors de l'application du choix: {e}")
                    # Continuer avec une action générique
                    current_action = (
                        "Reporter son attention sur les alentours immédiats."
                    )

                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"Erreur inattendue: {e}")
                # Continuer avec une action générique
                current_action = "Reporter son attention sur les alentours immédiats."
                await asyncio.sleep(1)

        # 3. Résumé final
        print("\n=== Résumé de la cohérence narrative ===")
        print("Éléments narratifs mentionnés:")
        for element, count in story_elements.items():
            print(f"- {element.replace('_', ' ')}: {count} fois")

        print("\nProgression des objectifs:")
        for objective, completed in objectives.items():
            status = "✅" if completed else "❌"
            print(f"- {objective.replace('_', ' ')}: {status}")

        print(f"\nPosition finale: {player_position}")

        try:
            player = next(
                p
                for p in requests.get(f"{BASE_URL}/games/{game_id}").json()["players"]
                if p["player_id"] == "player-1"
            )
            print(f"\nÉtat final: PV={player['hp']:.1f}, Mana={player['mp']:.1f}")
        except Exception:
            print("\nÉtat final: Impossible de récupérer les données du joueur")

    except Exception as e:
        logger.error(f"Erreur: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
