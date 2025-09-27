from random import randint

import requests

BASE_URL = "http://localhost:8000/v1"


def main():
    try:
        # Fetch available scenarios

        resp = requests.get(f"{BASE_URL}/scenarios")
        resp.raise_for_status()
        scenarios = resp.json()

        if not scenarios:
            print("No scenarios available. Please initialize the database first.")
            return
        print("Available scenarios:")
        for scenario in scenarios:
            print(f"- ID: {scenario['id']}, Name: {scenario['name']}")

        scenario_id = scenarios[0][
            "id"
        ]  # Just pick the first scenario for this example
        print(f"Using scenario ID: {scenario_id}")

        # Create a new game with the selected scenario

        game_data = {"scenario_id": scenario_id}
        resp = requests.post(f"{BASE_URL}/game", json=game_data)
        resp.raise_for_status()

        game = resp.json()
        print(f"Created game with ID: {game['id']} for scenario ID: {scenario_id}")

        # Create players for the game

        player_data = [
            {
                "display_name": "Hero1",
                "role": "Warrior",
                "hp": 100,
                "mp": 50,
                "game_id": game["id"],
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
                "game_id": game["id"],
                "stats": {
                    "strength": 5,
                    "intelligence": 15,
                    "dexterity": 10,
                    "charisma": 8,
                    "chance": 7,
                },
            },
        ]

        for pdata in player_data:
            resp = requests.post(f"{BASE_URL}/player", json=pdata)
            resp.raise_for_status()
            player = resp.json()
            print(
                f"Created player with ID: {player['id']} and name: {player['display_name']}"
            )

    except requests.RequestException as e:
        print(f"Error fetching scenarios: {e}")
        return
    except IndexError:
        print("No scenarios found in the response.")
        return
    except KeyError:
        print("Unexpected response format.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    # Roll dice for initiative
    try:
        resp = requests.post(f"{BASE_URL}/game/{game['id']}/roll_initiative")
        resp.raise_for_status()
        players = resp.json()
        print("Rolled initiative for players:")
        for player in players:
            print(
                f"- {player['display_name']} (Initiative: {player['initiative']}, Order: {player['order']})"
            )
    except requests.RequestException as e:
        print(f"Error rolling initiative: {e}")
        return
    except KeyError:
        print("Unexpected response format when rolling initiative.")
        return
    except Exception as e:
        print(f"An unexpected error occurred when rolling initiative: {e}")
        return

    # Play a turn
    ai_play_success: bool = False
    ai_play_success_retry_count: int = 0

    while not ai_play_success and ai_play_success_retry_count < 5:
        try:
            resp = requests.post(f"{BASE_URL}/game/{game['id']}/ai_turn")
            resp.raise_for_status()
            game_state = resp.json()
            print(
                f"Turn played. Game is now in phase: {game_state['phase']}, Turn: {game_state['turn']}"
            )
            ai_play_success = True
        except requests.RequestException as e:
            print(f"Error playing turn: {e}")
            print("Retrying AI turn...")
        except KeyError:
            print("Unexpected response format when playing turn.")
            print("Retrying AI turn...")
        except Exception as e:
            print(f"An unexpected error occurred when playing turn: {e}")
            print("Retrying AI turn...")

    else:
        if not ai_play_success:
            print("Failed to play AI turn after multiple attempts. Exiting.")
            return

    # Fetch game history

    try:
        resp = requests.get(f"{BASE_URL}/game/{game['id']}/history")
        resp.raise_for_status()
        history = resp.json()
        print("Game history entries:")
        for entry in history:
            temp_msg = f"- [{entry['timestamp']}] {entry['action_role']} (Success: {entry['success']}) - \n\tResult: {entry['result']['narration']}"
            for option in entry["result"]["options"]:
                temp_msg += f"\n\tOption: {option}"
            print(temp_msg)
    except requests.RequestException as e:
        print(f"Error fetching game history: {e}")
        return
    except KeyError:
        print("Unexpected response format when fetching game history.")
        return
    except Exception as e:
        print(f"An unexpected error occurred when fetching game history: {e}")
        return

    # Choix d'une option au hasard parmi les options proposées par l'IA
    try:
        if (
            history
            and "options" in history[-1]["result"]
            and history[-1]["result"]["options"]
        ):
            options = history[-1]["result"]["options"]

            # pick a random option

            chosen_option = randint(0, len(options) - 1)

            print(f"Chosen option: {chosen_option}")
            print(f"Option details: {options[chosen_option]}")

            resp = requests.post(
                f"{BASE_URL}/game/{game['id']}/player_turn",
                json={"option_id": options[chosen_option]["id"]},
            )
            resp.raise_for_status()
            game_state = resp.json()
            print(
                f"Player turn played. Game is now in phase: {game_state['phase']}, Turn: {game_state['turn']}"
            )
        else:
            print("No options available to choose from.")
    except requests.RequestException as e:
        print(f"Error playing player turn: {e}")
        return
    except KeyError:
        print("Unexpected response format when playing player turn.")
        return
    except Exception as e:
        print(f"An unexpected error occurred when playing player turn: {e}")
        return

    # Fetch game history

    try:
        resp = requests.get(f"{BASE_URL}/game/{game['id']}/history")
        resp.raise_for_status()
        history = resp.json()
        print("Game history entries:")
        for entry in history:
            temp_msg = f"- [{entry['timestamp']}] {entry['action_role']} (Success: {entry['success']}) - \n\tResult: {entry['result']['narration']}"
            for option in entry["result"]["options"]:
                temp_msg += f"\n\tOption: {option}"
            print(temp_msg)
    except requests.RequestException as e:
        print(f"Error fetching game history: {e}")
        return
    except KeyError:
        print("Unexpected response format when fetching game history.")
        return
    except Exception as e:
        print(f"An unexpected error occurred when fetching game history: {e}")
        return


if __name__ == "__main__":
    main()
