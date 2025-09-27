import time
from random import randint

import requests

BASE_URL = "http://localhost:8000/v1"
MAX_AI_RETRIES = 5


def safe_request(method, url, **kwargs):
    """Helper pour simplifier les requêtes HTTP avec gestion des erreurs."""
    try:
        resp = requests.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Request error ({method} {url}): {e}")
        return None


def play_ai_turn(game_id: str) -> dict | None:
    """Joue un tour IA avec retries en cas d’échec."""
    for attempt in range(1, MAX_AI_RETRIES + 1):
        result = safe_request("POST", f"{BASE_URL}/game/{game_id}/ai_turn")
        if result:
            print(f"✅ AI turn succeeded (attempt {attempt})")
            return result
        print(f"⚠️ AI turn failed (attempt {attempt}), retrying...")
        time.sleep(1)

    print("❌ AI turn failed after multiple retries.")
    return None


def play_player_turn(game_id: str, options: list[dict]) -> dict | None:
    """Choisit une option aléatoire et joue un tour joueur."""
    chosen_option = randint(0, len(options) - 1)
    print(f"🎲 Player chose option {chosen_option}: {options[chosen_option]}")

    return safe_request(
        "POST",
        f"{BASE_URL}/game/{game_id}/player_turn",
        json={"option_id": options[chosen_option]["id"]},
    )


def print_last_history(game_id: str):
    """Affiche la dernière entrée d’historique."""
    history = safe_request("GET", f"{BASE_URL}/game/{game_id}/history")
    if not history:
        return

    entry = history[-1]
    narration = entry["result"].get("narration", "")
    options = entry["result"].get("options", [])

    print(f"\n📜 [{entry['timestamp']}] Narration:")
    print(f"    {narration}")
    if options:
        print("    Options:")
        for opt in options:
            print(f"      - {opt}")
    print()


def main():
    # === Setup game ===
    scenarios = safe_request("GET", f"{BASE_URL}/scenarios")
    if not scenarios:
        print("⚠️ No scenarios available. Please initialize the database first.")
        return

    scenario_id = scenarios[0]["id"]
    print(f"🎮 Using scenario: {scenarios[0]['name']} ({scenario_id})")

    game = safe_request("POST", f"{BASE_URL}/game", json={"scenario_id": scenario_id})
    if not game:
        return
    game_id = game["id"]

    print(f"✅ Created game {game_id}")

    # === Create players ===
    players = [
        {
            "display_name": "Hero1",
            "role": "Warrior",
            "hp": 100,
            "mp": 50,
            "game_id": game_id,
            "stats": {
                "strength": 15,
                "intelligence": 5,
                "dexterity": 10,
                "charisma": 8,
                "chance": 7,
            },
        },
        {
            "display_name": "Hero2",
            "role": "Scientist",
            "hp": 80,
            "mp": 100,
            "game_id": game_id,
            "stats": {
                "strength": 5,
                "intelligence": 15,
                "dexterity": 10,
                "charisma": 8,
                "chance": 7,
            },
        },
    ]

    for pdata in players:
        player = safe_request("POST", f"{BASE_URL}/player", json=pdata)
        if player:
            print(f"👤 Created player {player['display_name']} ({player['id']})")

    # === Roll initiative ===
    rolled = safe_request("POST", f"{BASE_URL}/game/{game_id}/roll_initiative")
    if rolled:
        print("🎲 Initiative rolled:")
        for p in rolled:
            print(
                f"- {p['display_name']} (initiative={p['initiative']}, order={p['order']})"
            )

    # === Game loop ===
    print("\n🚀 Starting game loop...\n")
    while True:
        # --- IA turn ---
        game_state = play_ai_turn(game_id)
        if not game_state:
            break
        print_last_history(game_id)

        # --- Player turn ---
        history = safe_request("GET", f"{BASE_URL}/game/{game_id}/history")
        if not history:
            break
        last_entry = history[-1]
        options = last_entry["result"].get("options", [])

        if not options:
            print("⚠️ No options available, game may be over.")
            break

        game_state = play_player_turn(game_id, options)
        if not game_state:
            break
        print_last_history(game_id)

        # Stop if game is finished
        if game_state.get("active") is False:
            print("🏁 Game over!")
            break


if __name__ == "__main__":
    main()
