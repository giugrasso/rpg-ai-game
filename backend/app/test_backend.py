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
    try:
        resp = requests.post(f"{BASE_URL}/game/{game['id']}/ai_turn")
        resp.raise_for_status()
        game_state = resp.json()
        print(
            f"Turn played. Game is now in phase: {game_state['phase']}, Turn: {game_state['turn']}"
        )
    except requests.RequestException as e:
        print(f"Error playing turn: {e}")
        return
    except KeyError:
        print("Unexpected response format when playing turn.")
        return
    except Exception as e:
        print(f"An unexpected error occurred when playing turn: {e}")
        return

    # Fetch game history

    # TODO: Endpoint not implemented yet

    try:
        resp = requests.get(f"{BASE_URL}/game/{game['id']}/history")
        resp.raise_for_status()
        history = resp.json()
        print("Game history entries:")
        for entry in history:
            temp_msg = f"- [{entry['timestamp']}] {entry['action_type']} (Success: {entry['success']}) - \n\tResult: {entry['result']['narration']}"
            for option in entry['result']['options']:
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
