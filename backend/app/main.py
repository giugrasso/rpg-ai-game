# backend/app/main.py
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

# Ollama async client
from ollama import AsyncClient  # pip install ollama
from pydantic import BaseModel, Field

app = FastAPI(title="RPG AI Game - Scenario-driven Backend (Async Ollama)")

load_dotenv(".env")  # load env vars from .env file


# ---------------------------
# Models
# ---------------------------
class GameMode(str, Enum):
    PVE = "PvE"
    PVP = "PvP"


class CharacterRole(BaseModel):
    name: str
    stats: Dict[str, int]  # e.g. {"force":10, "intel":14}
    description: Optional[str] = None


class Scenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    mode: GameMode
    max_players: int
    roles: Dict[str, CharacterRole]  # role name -> role definition
    context: str  # big blob used to feed the AI (rules, lore, NPCs, objectives)


class Character(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    player_id: str
    display_name: str
    role: str
    stats: Dict[str, int]
    hp: int
    mp: Optional[int] = 0
    position: Optional[str] = "start"


class Game(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_id: str
    players: List[Character] = []
    turn: int = 0
    history: List[Dict] = []  # list of action dicts with timestamp
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class CreateGameRequest(BaseModel):
    scenario_id: str
    initial_players: Optional[List[Character]] = []


class ActionRequest(BaseModel):
    player_id: str
    action: str  # free text describing the action the player wants to take
    meta: Optional[Dict] = (
        None  # optional structured metadata (weapon, target, position, etc.)
    )


class AIResponse(BaseModel):
    narration: str
    rolls: Optional[List[Dict]] = None
    delta_state: Optional[List[Dict]] = None
    options: Optional[List[Dict]] = None


# ---------------------------
# In-memory "DB" (prototype)
# ---------------------------
SCENARIOS: Dict[str, Scenario] = {}
GAMES: Dict[str, Game] = {}

# ---------------------------
# Ollama client (singleton)
# ---------------------------
# You can configure host via env vars if needed, e.g. AsyncClient(host="http://ollama:11434")
ollama_client = AsyncClient(
    host="http://ollama:11434"
)  # default talks to localhost:11434


# ---------------------------
# Endpoints: Scenarios
# ---------------------------
@app.post("/scenarios", response_model=Scenario, status_code=201)
async def create_scenario(scenario: Scenario):
    if scenario.id in SCENARIOS:
        raise HTTPException(status_code=409, detail="Scenario already exists")
    SCENARIOS[scenario.id] = scenario
    return scenario


@app.get("/scenarios", response_model=List[Scenario])
async def list_scenarios():
    return list(SCENARIOS.values())


@app.get("/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: str):
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


# ---------------------------
# Endpoints: Games
# ---------------------------
@app.post("/games", response_model=Game, status_code=201)
async def create_game(req: CreateGameRequest):
    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if len(req.initial_players or []) > scenario.max_players:
        raise HTTPException(
            status_code=400, detail="Too many initial players for scenario"
        )

    game = Game(scenario_id=scenario.id, players=req.initial_players or [])
    GAMES[game.id] = game
    return game


@app.get("/games", response_model=List[Game])
async def list_games():
    return list(GAMES.values())


@app.get("/games/{game_id}", response_model=Game)
async def get_game(game_id: str):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.post("/games/{game_id}/join", response_model=Game)
async def join_game(game_id: str, character: Character):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    scenario = SCENARIOS.get(game.scenario_id)
    if not scenario:
        raise HTTPException(status_code=500, detail="Scenario missing")

    if len(game.players) >= scenario.max_players:
        raise HTTPException(status_code=400, detail="Game is full")

    # validate role exists in scenario
    if character.role not in scenario.roles:
        raise HTTPException(
            status_code=400, detail="Role not allowed for this scenario"
        )

    game.players.append(character)
    game.last_updated = datetime.utcnow()
    return game


# ------------------------------
# JSON Schema pour réponses Ollama
# ------------------------------
AI_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "narration": {"type": "string"},
        "delta_state": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "actor": {"type": "string"},
                    "hp": {"type": "number"},
                    "hp_set": {"type": "number"},
                    "position": {"type": "string"},
                },
            },
        },
        "rolls": {"type": "array"},
        "options": {"type": "array"},
    },
}


# ------------------------------
# Build prompt pour l'action
# ------------------------------
def build_prompt_for_action(
    scenario: Scenario, game: Game, action: ActionRequest
) -> str:
    prompt = f"Scenario: {scenario.name}\n"
    prompt += f"Description: {scenario.description}\n"
    prompt += "Players:\n"
    for p in game.players:
        prompt += f"- {p.display_name} ({p.role}) HP:{p.hp} MP:{p.mp} Stats:{p.stats}\n"
    prompt += f"\nAction by {action.player_id}: {action.action}\n"
    prompt += (
        "Respond in JSON format with fields: narration, delta_state, rolls, options."
    )
    return prompt


# ------------------------------
# Endpoint: Action
# ------------------------------
@app.post("/games/{game_id}/action", response_model=AIResponse)
async def game_action(game_id: str, action: ActionRequest):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    scenario = SCENARIOS.get(game.scenario_id)
    if not scenario:
        raise HTTPException(status_code=500, detail="Scenario not found")

    player = next((p for p in game.players if p.player_id == action.player_id), None)
    if not player:
        raise HTTPException(status_code=400, detail="Player not part of this game")

    prompt = build_prompt_for_action(scenario, game, action)

    # ------------------------------
    # Appel Ollama Async avec format JSON
    # ------------------------------
    import json

    try:
        resp = await ollama_client.generate(
            model=os.getenv("OLLAMA_MODEL", "game_master"),
            prompt=prompt,
            stream=False,
            format=AI_OUTPUT_SCHEMA,
        )

        raw_response = getattr(resp, "response", None) or resp
        if isinstance(raw_response, dict):
            parsed = raw_response
        elif isinstance(raw_response, str):
            parsed = json.loads(raw_response)
        else:
            parsed = json.loads(str(raw_response))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ollama call failed: {exc}")

    # ------------------------------
    # Appliquer delta_state
    # ------------------------------
    for change in parsed.get("delta_state") or []:
        actor_id = change.get("actor")
        for p in game.players:
            if p.player_id == actor_id:
                if "hp" in change and isinstance(change["hp"], int):
                    p.hp = max(0, p.hp + change["hp"])
                if "hp_set" in change:
                    p.hp = int(change["hp_set"])
                if "position" in change:
                    p.position = change["position"]

    # Append to history
    game.history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "actor": action.player_id,
            "action": action.action,
            "ai_narration": parsed.get("narration"),
        }
    )
    game.turn += 1
    game.last_updated = datetime.utcnow()

    return AIResponse(
        narration=parsed.get("narration", ""),
        rolls=parsed.get("rolls", []),
        delta_state=parsed.get("delta_state", []),
        options=parsed.get("options", []),
    )


@app.get("/games/{game_id}/history", response_model=List[Dict])
async def game_history(game_id: str):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.history


@app.get("/config/get_model")
async def get_ollama_model():
    resp = requests.get("http://ollama:11434/api/tags")
    resp.raise_for_status()
    models = resp.json()
    print(models)
    for m in models["models"]:
        print(m)
        if m.get("name") == "game_master:latest":
            return {"model_exists": True}
    raise HTTPException(status_code=404, detail="Master model not found")


@app.post("/config/set_model")
async def set_ollama_model():
    payload = {
        "model": "game_master",
        "from": "llama3.2",
        "system": (
            "Tu es un maître du jeu pour des parties de jeux de rôle. Tu fournis des descriptions immersives, gères les règles, et crées des scénarios captivants pour les joueurs. Adapte tes réponses en fonction du contexte et des actions des joueurs."
        ),
    }

    # headers = {"Content-Type": "application/json"}

    try:
        resp = requests.request(
            "POST", "http://ollama:11434/api/create", json=payload
        )
        resp.raise_for_status()
    except Exception as exc:
        return {"status": f"failed to create model: {exc}"}

    return {"status": "model game_master created based on llama3.2"}


# ---------------------------
# Simple example to prefill a scenario
# ---------------------------
@app.on_event("startup")
async def startup_event():
    # create a demo StarWars-like scenario as illustration
    sc = Scenario(
        name="L'ile des dinosaures",
        description="Une ile mystérieuse peuplée de dinosaures issus d'une expérience scientifique.",
        mode=GameMode.PVE,
        max_players=4,
        roles={
            "Chasseur": CharacterRole(
                name="Chasseur",
                stats={"force": 18, "intel": 12, "charisma": 14},
                description="Utilise des armes à feu et des pièges",
            ),
            "Scientifique": CharacterRole(
                name="Scientifique",
                stats={"force": 10, "intel": 18, "charisma": 12},
                description="Expert en biologie et en technologie",
            ),
        },
        context=(
            "Les joueurs sont arrivé de nuit par le port sur une ile tropicale où des expériences génétiques ont mal tourné, libérant des dinosaures. "
            "Les joueurs doivent coopérer pour survivre, explorer l'ile, et trouver un scientifique qui s'appelle George et se rendre à l'héliport "
            "qui se trouve dans le centre de l'ile. Les règles incluent des jets de dés pour les actions risquées, la gestion des ressources (nourriture, eau), "
            "et des rencontres aléatoires avec des dinosaures hostiles. Les joueurs peuvent utiliser leurs compétences spéciales en fonction de leur rôle."
        ),
    )
    SCENARIOS[sc.id] = sc
