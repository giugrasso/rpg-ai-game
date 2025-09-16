# backend/app/main.py
import asyncio
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

# Ollama async client
from ollama import AsyncClient  # pip install ollama

app = FastAPI(title="RPG AI Game - Scenario-driven Backend (Async Ollama)")


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
ollama_client = AsyncClient(host="http://ollama:11434")  # default talks to localhost:11434


# # ---------------------------
# # Helper: build prompt for Ollama
# # ---------------------------
# def build_prompt_for_action(
#     scenario: Scenario, game: Game, action_req: ActionRequest
# ) -> str:
#     """
#     Compose a prompt that contains:
#       - scenario.context (world description, rules)
#       - concise current game state (turn, players with hp/stats)
#       - short history (last N actions)
#       - the player's current requested action
#       - an instruction to return structured JSON (narration, delta_state, options)
#     """
#     # compact state
#     players_state = []
#     for p in game.players:
#         players_state.append(
#             f"{p.display_name} (id={p.id}, role={p.role}, hp={p.hp}, stats={p.stats}, pos={p.position})"
#         )
#     last_actions = game.history[-10:]  # last up to 10 actions
#     last_actions_text = "\n".join(
#         [f"- [{a['timestamp']}] {a['actor']}: {a['action']}" for a in last_actions]
#     )

#     prompt = f"""
# You are the scenario Game Master. Use the provided Scenario context and the current game state to resolve the player's action.
# Scenario: {scenario.name}
# Context: {scenario.context}

# Current Game State (turn {game.turn}):
# Players:
# {chr(10).join(players_state)}

# Recent actions:
# {last_actions_text if last_actions_text else '- none'}

# Player action request:
# Player id: {action_req.player_id}
# Action: {action_req.action}
# Meta: {action_req.meta}

# INSTRUCTIONS (important):
# - Resolve the action using the scenario rules.
# - Provide a concise narration (1-3 sentences).
# - Provide any dice rolls you simulated (type and value).
# - Provide a delta_state array describing minimal changes to apply (e.g. [{{'actor':'char-id','hp':-5}}]).
# - Provide two follow-up options players can choose with short descriptions.
# - Return the response in valid JSON object ONLY, with keys: narration, rolls, delta_state, options.

# Respond in JSON only.
# """
#     return prompt.strip()


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
def build_prompt_for_action(scenario: Scenario, game: Game, action: ActionRequest) -> str:
    prompt = f"Scenario: {scenario.name}\n"
    prompt += f"Description: {scenario.description}\n"
    prompt += f"Players:\n"
    for p in game.players:
        prompt += f"- {p.display_name} ({p.role}) HP:{p.hp} MP:{p.mp} Stats:{p.stats}\n"
    prompt += f"\nAction by {action.player_id}: {action.action}\n"
    prompt += "Respond in JSON format with fields: narration, delta_state, rolls, options."
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
            model="llama3.2:latest",
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


# ---------------------------
# Simple example to prefill a scenario
# ---------------------------
@app.on_event("startup")
async def startup_event():
    # create a demo StarWars-like scenario as illustration
    sc = Scenario(
        name="Starfield Skirmish",
        description="Sci-fi skirmish scenario (demo).",
        mode=GameMode.PVE,
        max_players=4,
        roles={
            "Jedi": CharacterRole(
                name="Jedi",
                stats={"force": 18, "intel": 12, "charisma": 14},
                description="Lightsaber user",
            ),
            "Rebel": CharacterRole(
                name="Rebel",
                stats={"force": 10, "intel": 14, "charisma": 12},
                description="Marksman",
            ),
        },
        context=(
            "You are on a frozen outpost. Rebels defend against Imperial raiders. "
            "Rules: one main action per turn. Resolve using virtual d20 when appropriate. "
            "Provide structured JSON outputs when requested."
        ),
    )
    SCENARIOS[sc.id] = sc
