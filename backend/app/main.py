from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Game API")


# Modèle simple pour un joueur
class Player(BaseModel):
    id: int
    name: str


# Liste en mémoire pour tester
players_db: List[Player] = []


@app.get("/players", response_model=List[Player])
def get_players():
    """
    Retourne la liste de tous les joueurs.
    """
    return players_db


@app.post(
    "/players",
    response_model=Player,
    status_code=201,
    responses={
        409: {
            "description": "Player with this ID already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Player with this ID already exists.",
                    }
                }
            },
        }
    },
)
def add_player(player: Player):
    """
    Ajoute un joueur à la liste.
    """
    if any(p.id == player.id for p in players_db):
        raise HTTPException(
            status_code=409, detail="Player with this ID already exists."
        )

    players_db.append(player)
    return player
