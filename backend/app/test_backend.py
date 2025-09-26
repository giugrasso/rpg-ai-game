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


if __name__ == "__main__":
    main()
