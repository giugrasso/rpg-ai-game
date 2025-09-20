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

AI_MODEL = os.getenv("OLLAMA_MODEL", "LLAMA3.2")  # default model if not set in env


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
    objectives: str
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
    hp: float
    mp: float
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


class Options(BaseModel):
    id: int
    description: str
    success_rate: float  # estimated success rate (0.0 to 1.0)
    health_point_change: float  # e.g. -10 for damage, +5 for healing
    mana_point_change: float  # e.g. -5 for spell cost, +3 for regen
    related_stat: str  # e.g. "force", "intelligence", etc.


class AIResponse(BaseModel):
    narration: str
    options: Optional[List[Options]]


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
# Build prompt pour l'action
# ------------------------------
def build_prompt_for_action(
    scenario: Scenario, game: Game, action: ActionRequest
) -> str:
    prompt = f"Scenario: {scenario.name}\n"
    prompt += f"Description: {scenario.description}\n"
    prompt += f"Context: {scenario.context}\n"
    prompt += f"Objectives: {scenario.objectives}\n"
    prompt += "Players:\n"
    for p in game.players:
        prompt += f"- ID:{p.player_id} Nom:{p.display_name} ({p.role}) HP:{p.hp} MP:{p.mp} Stats:{p.stats}\n"
    prompt += f"\nAction by {action.player_id}: {action.action}\n"
    # prompt += (
    #     "Repond au format JSON en complétant tous les champs"
    # )
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

    print(f"=== Prompt sent to Ollama ===\n{prompt}\n")

    # ------------------------------
    # Appel Ollama Async avec format JSON
    # ------------------------------
    import json

    try:
        resp = await ollama_client.generate(
            model="game_master",
            prompt=prompt,
            stream=False,
            format=None,  # important pour gpt-oss
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
        "from": AI_MODEL,
        "system": (
f"""Tu es un maître du jeu (MJ) expert en jeux de rôle.

Ton rôle est de créer une narration immersive et dynamique.

À chaque tour, tu dois :

    1. Décrire l'environnement, les personnages, et les événements de manière vivante et sensorielle.
    2. Adapter l'histoire au scénario choisi (ex: fantasy, science-fiction, horreur...), en respectant l'objectif global défini pour la partie.
    3. Prendre en compte les caractéristiques, compétences et équipement des joueurs, ainsi que leurs décisions et les conséquences des choix précédents.
    4. Proposer aux joueurs plusieurs options claires et déterminantes qui influencent la suite de l'aventure.
    5. En cas de combat ou d'action risquée, intégrer des mécaniques de jet de dés (ex: d20) et donner un retour chiffré ou narratif sur le résultat.
    6. Si un joueur fournit une réponse absurde, incohérente ou hors contexte, ne casse jamais l'immersion. Interprète cela comme un signe qu'il a été empoisonné, hypnotisé, ensorcelé ou qu'il sombre dans la folie. Propose des choix qui remettent subtilement le joueur sur la voie de l'objectif et fixe un success_rate à 0.0 si le joueur propose une action absurde ou hors contexte.
    7. Le joueur possède des statistiques. Il doit toujours avoir au minimum 2 options pour continuer l'aventure. Chaque option doit être en lien avec une statistique.

Règles importantes :

    - Tes réponses doivent être immersives, captivantes, et donner envie de continuer à jouer.
    - Ne révèle jamais le scénario à l'avance.
    - Laisse toujours aux joueurs l'opportunité de choisir leur chemin.
    - Réponds en français pour les options et la narration.
    - Le success_rate est une estimation de la probabilité de réussite d'une action allant de 0.0 à 1.0 (1.0 = succès certain, 0.0 = échec certain).
    - Le health_point_change est un multiplicateur de points de vie allant de -1.0 à 1.0 (négative pour les dégâts, positive pour la guérison) (health_point_change à 1.0 restaure toute la vie. health_point_change à -1.0 retire toute la vie du joueur en le tuant.).
    - Le mana_point_change est un multiplicateur de points de mana (ou d'énergie) allant de -1.0 à 1.0 (négative pour le coût en mana, positive pour la régénération) (mana_point_change à 1.0 restaure tout le mana (ou d'énergie). mana_point_change à -1.0 retire tout le mana (ou d'énergie) du joueur en l'empechant de prendre une autre action autre que se reposer ou prendre utiliser un objet qui restore du mana (ou d'énergie).).
    - Ne modifie pas les points de vie ou de mana en dehors des actions de combat.
    - Produis uniquement du JSON strictement valide.
        Ne mets aucun texte avant ni après. 

        Voici le schéma attendu :
        {AIResponse.model_json_schema()}
"""
        ),
    }

    # headers = {"Content-Type": "application/json"}

    try:
        resp = requests.request("POST", "http://ollama:11434/api/create", json=payload)
        resp.raise_for_status()
    except Exception as exc:
        return {"status": f"failed to create model: {exc}"}

    return {"status": f"model game_master created based on {AI_MODEL}"}


# ---------------------------
# Simple example to prefill a scenario
# ---------------------------
@app.on_event("startup")
async def startup_event():
    # create a demo StarWars-like scenario as illustration
    sc = Scenario(
        name="L'ile des dinosaures",
        description="Une ile mystérieuse peuplée de dinosaures issus d'une expérience scientifique.",
        objectives="Survivre, trouver le scientifique George, et atteindre l'héliport.",
        mode=GameMode.PVE,
        max_players=4,
        roles={
            "Chasseur": CharacterRole(
                name="Chasseur",
                stats={
                    "force": 18,
                    "intelligence": 12,
                    "charisme": 14,
                    "courage": 16,
                    "chance": 10,
                },
                description="Utilise des armes à feu et des pièges",
            ),
            "Scientifique": CharacterRole(
                name="Scientifique",
                stats={
                    "force": 10,
                    "intelligence": 18,
                    "charisme": 12,
                    "courage": 8,
                    "chance": 14,
                },
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
