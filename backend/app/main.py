# backend/app/main.py
import json
import logging
import os
import random
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status

# Ollama async client
from ollama import AsyncClient  # pip install ollama
from pydantic import BaseModel, Field, field_validator

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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


class Option(BaseModel):
    id: int
    description: str
    success_rate: float = Field(ge=0.0, le=1.0)  # estimated success rate (0.0 to 1.0)
    health_point_change: float = Field(ge=-1.0, le=1.0)
    mana_point_change: float = Field(ge=-1.0, le=1.0)
    related_stat: str  # e.g. "force", "intelligence", etc.


class AIResponse(BaseModel):
    narration: str
    options: List[Option] = []

    @field_validator("options", mode="before")
    def validate_options(cls, v):
        if v is None:
            return []
        return v


class ChooseOptionRequest(BaseModel):
    player_id: str
    option_id: int


class DiceRoll(BaseModel):
    roll: int
    success: bool
    narration: str


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
    logger.info(f"Scenario created: {scenario.id}")
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
    logger.info(f"Game created: {game.id}")
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
    logger.info(f"Player {character.player_id} joined game {game_id}")
    return game


# ------------------------------
# Build prompt pour l'action
# ------------------------------
def build_chat_messages(scenario: Scenario, game: Game, action: ActionRequest, player: Character) -> list:

    """Construit les messages de chat avec tout l'historique de la conversation"""
    messages = []

    # Ajouter l'historique complet des actions précédentes
    for turn, past_action in enumerate(game.history):
        messages.append({
            "role": "user",
            "content": f"""
            Tour {turn + 1} - Action du joueur {past_action['actor']}:
            {past_action['action']}
            """
        })

        messages.append({
            "role": "assistant",
            "content": f"""
            {{
              "narration": "{past_action['ai_narration']}",
              "options": {json.dumps(past_action['options'])}
            }}
            """
        })

    # Ajouter l'action actuelle
    messages.append({
        "role": "user",
        "content": f"""
        Tour {game.turn + 1} - Nouvelle action:
        Joueur: {action.player_id} ({player.role})
        Position: {player.position or 'inconnue'}
        Stats: {player.stats}
        PV: {player.hp}/100, Mana: {player.mp}/100

        Action: "{action.action}"

        Instructions:
        1. Décris la scène en 3-5 phrases riches en détails sensoriels
        2. Propose 2-3 options d'action avec:
           - Une description claire et immersive
           - Un success_rate basé sur les stats du joueur
           - Des conséquences réalistes (ΔPV/ΔMana)
        3. Assure-toi que tes options permettent de progresser vers l'objectif: "{scenario.objectives}"
        """
    })

    return messages

def create_fallback_response(game: Game, player: Character, action: ActionRequest) -> AIResponse:
    """Crée une réponse par défaut en cas d'échec du parsing"""
    return AIResponse(
        narration=f"""
        {player.display_name} tente de {action.action.lower()}, mais quelque chose ne se passe pas comme prévu...
        La jungle semble réagir à votre présence. Des bruits étranges résonnent entre les arbres,
        et une odeur métallique flotte dans l'air. Vous devez décider de votre prochaine action.
        """,
        options=[
            Option(
                id=1,
                description="Explorer prudemment les alentours pour trouver des indices",
                success_rate=0.7,
                health_point_change=0.0,
                mana_point_change=0.0,
                related_stat="intelligence"
            ),
            Option(
                id=2,
                description="Se diriger vers la source des bruits étranges",
                success_rate=0.4,
                health_point_change=-0.1,
                mana_point_change=0.0,
                related_stat="courage"
            )
        ]
    )


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

    # Trouver le joueur
    player = next((p for p in game.players if p.player_id == action.player_id), None)
    if not player:
        raise HTTPException(status_code=400, detail="Player not part of this game")

    # Construire les messages de chat avec tout l'historique
    messages = build_chat_messages(scenario, game, action, player)

    try:
        # Utiliser l'API chat avec l'historique complet
        response = await ollama_client.chat(
            model="game_master",
            messages=messages,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "seed": 42  # Pour une meilleure cohérence
            }
        )

        # Extraire et valider la réponse
        raw_response = response['message']['content']
        logger.debug(f"Raw AI response: {raw_response}")

        try:
            parsed = AIResponse.model_validate_json(raw_response)
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Tentative de récupération
            try:
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    parsed = AIResponse.model_validate_json(json_match.group(0))
                else:
                    parsed = create_fallback_response(game, player, action)
            except Exception as e2:
                logger.error(f"Manual extraction failed: {e2}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Impossible de traiter la réponse de l'IA"
                )

        # Mettre à jour l'historique avec la réponse
        game.history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "actor": action.player_id,
            "action": action.action,
            "ai_narration": parsed.narration,
            "options": [opt.model_dump() for opt in parsed.options],
            "context": {
                "scenario": scenario.name,
                "player_stats": player.stats,
                "player_position": player.position or "unknown",
                "turn": game.turn
            }
        })

        game.turn += 1
        game.last_updated = datetime.utcnow()
        return parsed

    except Exception as exc:
        logger.error(f"Ollama chat failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur avec l'API chat: {str(exc)[:200]}"
        )


# Ajoutez cette fonction pour extraire manuellement une réponse valide
def extract_ai_response_manually(raw_response: str) -> AIResponse:
    """Essaie d'extraire une réponse valide même si le format est incorrect"""
    try:
        # Essayer de trouver la narration
        narration_match = re.search(
            r'"narration"\s*:\s*"(.*?)"', raw_response, re.DOTALL
        )
        narration = (
            narration_match.group(1)
            if narration_match
            else "Réponse narrative non disponible"
        )

        # Essayer de trouver les options
        options = []
        option_matches = re.finditer(
            r'\{.*?"id"\s*:\s*(\d+).*?"description"\s*:\s*"(.*?)"',
            raw_response,
            re.DOTALL,
        )

        for match in option_matches:
            try:
                option_data = {
                    "id": int(match.group(1)),
                    "description": match.group(2),
                    "success_rate": 0.5,  # Valeur par défaut
                    "health_point_change": 0.0,  # Valeur par défaut
                    "mana_point_change": 0.0,  # Valeur par défaut
                    "related_stat": "intelligence",  # Valeur par défaut
                }
                options.append(option_data)
            except Exception:
                continue

        # Si aucune option n'est trouvée, créer une option par défaut
        if not options:
            options = [
                {
                    "id": 1,
                    "description": "Continuer l'exploration",
                    "success_rate": 0.7,
                    "health_point_change": 0.0,
                    "mana_point_change": 0.0,
                    "related_stat": "chance",
                }
            ]

        return AIResponse(narration=narration, options=[Option(**opt) for opt in options])

    except Exception as e:
        logger.error(f"Échec de l'extraction manuelle: {e}")
        # Retourner une réponse minimale valide
        return AIResponse(
            narration="L'IA a rencontré un problème technique. Veuillez réessayer.",
            options=[
                Option(
                    id=1,
                    description="Continuer malgré le problème technique",
                    success_rate=0.5,
                    health_point_change=0.0,
                    mana_point_change=0.0,
                    related_stat="chance",
                )
            ],
        )


@app.get("/games/{game_id}/history", response_model=List[Dict])
async def game_history(game_id: str):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.history


@app.get("/config/get_model")
async def get_ollama_model():
    """Check if the custom Ollama model exists."""
    try:
        resp = requests.get("http://ollama:11434/api/tags")
        resp.raise_for_status()
        models = resp.json()
        for m in models["models"]:
            if m.get("name") == "game_master:latest":
                return {"model_exists": True}
        return {"model_exists": False}
    except Exception as exc:
        logger.error(f"Failed to check Ollama model: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check Ollama model: {exc}",
        )


@app.post("/config/set_model")
async def set_ollama_model():
    payload = {
        "model": "game_master",
        "from": AI_MODEL,
        "system": f"""
⚠️ RÈGLE ABSOLUE : TU DOIS **TOUJOURS** répondre avec un JSON valide **ET RIEN D'AUTRE**.
Ne commence **JAMAIS** ta réponse par du texte comme "Voici la réponse :", "Le joueur voit...", ou toute autre narration en dehors du JSON.
Si tu ne respectes pas cette règle, le jeu ne fonctionnera pas.

---
### Rôle et Responsabilités
Tu es un **maître du jeu (MJ) expert** pour un jeu de rôle narratif. Ton objectif est de :
1. **Créer une immersion totale** en décrivant les scènes, personnages et événements avec des détails **sensoriels** (sons, odeurs, textures, ambiance).
2. **Adapter dynamiquement l'histoire** au scénario, aux actions des joueurs et à leurs statistiques.
3. **Guider subtilement les joueurs vers l'objectif principal** du scénario **sans le révéler explicitement**.
    - Utilise des indices environnementaux (ex : "Un bruit vient de la direction de ton objectif...").
    - Évite les digressions qui n'avancent pas l'histoire.
4. **Respecter les règles du monde** (ex : pas de magie dans un scénario scientifique, pas de technologie futuriste dans un monde médiéval).
5. **Gérer les actions risquées** (combats, pièges, négociations) avec des mécaniques de succès/échec basées sur les statistiques des joueurs.

---
### Structure de Réponse Obligatoire
Ton JSON doit **toujours** suivre ce schéma :
{AIResponse.model_json_schema()}

---
### Règles pour les Options
- **Nombre** : Propose **toujours 2 ou 3 options** (sauf cas exceptionnel justifié par le scénario).
- **Variété** :
    - Une option doit avoir un `success_rate` **élevé** (> 0.6) et un risque faible.
    - Une option doit avoir un `success_rate` **faible** (< 0.4) mais un gain potentiel important.
    - Les valeurs de `health_point_change`/`mana_point_change` doivent être **cohérentes** avec le risque (ex : une attaque puissante a un `health_point_change` négatif élevé).
- **Lien avec les stats** :
    - `related_stat` doit correspondre à une statistique du joueur (ex : "force" pour un combat, "intelligence" pour résoudre une énigme).
    - Une option ne peut pas dépendre d'une stat que le joueur n'a pas.
- **Cohérence** :
    - Les effets (`health_point_change`, `mana_point_change`) doivent être **réalistes** dans le contexte (ex : une potion de soin ne restaure pas 100% des PV si le scénario est difficile).
    - Si une action est impossible (ex : "voler sans ailes"), fixe `success_rate=0.0` et propose des alternatives.

---

### Règles spéciales pour les échecs
1. EN CAS D'ÉCHEC D'UNE ACTION :
   - Décris uniquement la conséquence de l'échec dans la narration.
   - NE METS PAS de schéma JSON ou d'explications sur le format.
   - Respecte STRICTEMENT le format requis :
{AIResponse.model_json_schema()}
   - Les options doivent refléter les conséquences de l'échec (ex: 'Se soigner', 'Fuir', 'Tenter une autre approche')."

---
### Gestion des Cas Spéciaux
- **Actions absurdes/hors contexte** :
    - Narration : Décris l'échec de manière immersive (ex : "Ton personnage, sous l'emprise d'une illusion, tente de parler aux murs...").
    - Options : Propose des moyens de **revenir à une situation normale** (ex : "Secouer la tête pour te ressaisir").
    - `success_rate` : 0.0 pour l'action absurde, > 0.5 pour les options de rattrapage.
- **Objectif du scénario** :
    - Toutes les options doivent **indirectement rapprocher** les joueurs de l'objectif (même après un échec).
    - Utilise des PNJ, des événements ou des indices pour **recadrer l'histoire** si les joueurs s'éloignent trop.
- **Combats/Conflits** :
    - Décris les ennemis, leur état (blessés, enragés, affaiblis) et les conséquences des actions.
    - Les dégâts (`health_point_change`) doivent être **proportionnels** à la menace (ex : un boss inflige plus de dégâts qu'un ennemi basique).

---
### Consignes Supplémentaires
- **Langue** : Réponds **uniquement en français**, avec un style **vivant et captivant**.
- **Équilibre** :
    - Un joueur ne doit **jamais** être bloqué sans solution (même après un échec).
    - Les récompenses/risques doivent être **équilibrés** (ex : un trésor bien gardé a un haut risque mais une grande récompense).
- **Dynamicité** :
    - Fais évoluer l'environnement en fonction des actions (ex : un dinosaure blessé peut fuir ou devenir plus agressif).
    - Les PNJ ont des personnalités et réagissent de manière cohérente (ex : un scientifique aura peur des dinosaures).
- **Immersion** :
    - Utilise des **métaphores** et des **comparaisons** pour rendre les descriptions plus vivantes (ex : "Le rugissement du raptor ressemble à un moteur qui tousse").
    - Varier les sens utilisés (ouïe, odorat, toucher) pour enrichir l'expérience.

---
### Interdictions Formelles
- ❌ **Ne révèle JAMAIS** l'objectif du scénario ou des éléments clés à l'avance.
- ❌ **Ne brise JAMAIS l'immersion** (même pour une action absurde, trouve une explication narrative).
- ❌ **Ne dépasse JAMAIS** les limites des multiplicateurs :
    - `health_point_change` et `mana_point_change` doivent toujours être entre **-1.0 et 1.0**.
    - `success_rate` doit toujours être entre **0.0 et 1.0**.
- ❌ **N'invente pas** de nouvelles statistiques ou compétences pour les joueurs.
""",
    }

    # headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post("http://ollama:11434/api/create", json=payload)
        resp.raise_for_status()
        logger.info("Custom Ollama model created successfully.")
        return {"status": f"model game_master created based on {AI_MODEL}"}
    except Exception as exc:
        logger.error(f"Failed to create Ollama model: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model: {exc}",
        )


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
        context="""
**Contexte connu des joueurs (à révéler progressivement) :**
Vous venez de débarquer de nuit sur une île tropicale isolée, après avoir répondu à un appel de détresse lancé par une station de recherche scientifique.
Le message était incomplet, mais mentionnait une "urgence biologique" et une évacuation par héliport au centre de l'île.
Votre mission initiale : localiser le Dr. George, le responsable de la station, et vous rendre à l'héliport pour une extraction d'urgence.

**Ce que les joueurs ignorent (à découvrir via l'exploration) :**
- L'île abritait un **projet de recherche secret** sur la **résurrection d'espèces éteintes**, financé par une organisation inconnue.
- Une **panne de courant générale** a plongé les installations dans le chaos il y a 48 heures. Depuis, plus aucun contact avec l'extérieur.
- Les systèmes de sécurité sont hors ligne, et les **portes des enclos de quarantaine** se sont ouvertes...
- Des **bruits étranges** (grondements, craquements de végétation) résonnent dans la jungle, surtout la nuit.
- Les rares notes retrouvées parlent de "sujets d'expérience non contrôlés" et de "protocole Ichthyosaure" (un code interne).

**Éléments clés à découvrir :**
- **George** : Le scientifique en chef. D'après les transmissions interceptées, il se dirigeait vers le **bunker central** (près de l'héliport) avec des échantillons "critiques".
  - *Indices pour le trouver* :
    - Une carte partielle de l'île (trouvable dans le camp de base) montre un chemin vers le centre.
    - Des **traces de pas humains** récentes mènent vers les collines centrales.
    - Des **messages audio** dispersés (via talkies-walkies) mentionnent un "protocole d'urgence activé".
- **L'héliport** : Situé au cœur de l'île, c'est le seul point d'évacuation. Son générateur de secours clignote encore, visible de loin la nuit.
  - *Obstacles* :
    - La jungle est dense, avec des **zones marquées "DANGER - ACCÈS RESTREINT"** (anciens enclos).
    - Des **câbles électriques arrachés** et des **équipements endommagés** jonchent les sentiers.
- **Ressources** :
  - Nourriture et eau sont limitées. Les joueurs devront **piller les caches de la station** ou chasser (avec des risques).
  - Des **armoires médicales** (dans les avant-postes) contiennent des soins, mais certaines sont vides... ou ouvertes de l'intérieur.
- **Règles de survie** :
  - **Jets de dés** : Toute action risquée (escalade, combat, fouille) dépend des stats des joueurs.
  - **Gestion des ressources** : Un inventaire limité force à faire des choix (ex : garder une lampe torche ou des munitions).
  - **Rencontres aléatoires** : Des **bruits inexpliqués** (feuillages qui bougent, souffles chauds) peuvent survenir, surtout près des zones restreintes.

**Ambiance à instaurer :**
- **Jour** : L'île semble déserte, mais des détails trahissent une présence (ex : branches cassées à 3 mètres de haut, odeurs musquées).
- **Nuit** : Les bruits s'intensifient. Une **lueur verdâtre** émane parfois des zones restreintes...
- **Indices environnementaux** :
  - Des **cages vides** (portes arrachées) près des laboratoires.
  - Des **cadavres d'animaux** (moutons, singes) partiellement dévorés, avec des morsures anormalement larges.
  - Des **écrans de surveillance** (si réactivés) montrent des silhouettes se déplaçant rapidement entre les arbres.

**Objectif caché (pour le MJ) :**
- Les "sujets d'expérience" sont des **dinosaures génétiquement modifiés**, conçus pour être dociles... jusqu'à la panne.
- George sait comment les neutraliser (via un **émetteur à ultrasons** dans son labo), mais il est blessé et traqué.
- L'héliport a un **système de verrouillage** nécessitant un code (que George possède).

**Ton en tant que MJ :**
- Décris l'île comme **belle mais inquiétante** : plages de sable blanc contrastant avec des bâtiments vandalisés, odeurs de jungle mélangées à un **arôme métallique** (sang ? produits chimiques ?).
- Utilise des **métaphores** pour évoquer les dinosaures sans les nommer :
  - *"Un grognement sourd fait vibrer le sol, comme un moteur diesel au ralenti."*
  - *"Une ombre massive passe entre les arbres, trop grande pour un humain..."*
- Révèle la vérité **progressivement** :
  1. D'abord des **indices indirects** (empreintes, bruits).
  2. Puis des **aperçus** (queue qui disparaît dans les buissons).
  3. Enfin, une **rencontre claire** (ex : un raptor bloquant le chemin de l'héliport).
""",
    )
    SCENARIOS[sc.id] = sc
    logger.info(f"Demo scenario created: {sc.id}")


# Modifiez l'endpoint /games/{game_id}/choose comme suit
@app.post("/games/{game_id}/choose", response_model=Game)
async def choose_option(game_id: str, req: ChooseOptionRequest):
    game = GAMES.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    player = next((p for p in game.players if p.player_id == req.player_id), None)
    if not player:
        raise HTTPException(status_code=400, detail="Player not part of this game")

    if not game.history:
        raise HTTPException(status_code=400, detail="No action history found")

    last_action = game.history[-1]
    if "options" not in last_action or not last_action["options"]:
        raise HTTPException(status_code=400, detail="No options available in history")

    option_id = int(req.option_id)

    # Trouver l'option choisie
    chosen_option = next(
        (opt for opt in last_action["options"] if int(opt["id"]) == option_id),
        None,
    )
    if not chosen_option:
        available_ids = [int(opt["id"]) for opt in last_action["options"]]
        raise HTTPException(
            status_code=400,
            detail=f"Option {option_id} not found. Available IDs: {available_ids}",
        )

    # Calculer le succès de l'action
    stat_value = player.stats.get(
        chosen_option["related_stat"], 10
    )  # Valeur par défaut si stat non trouvée
    base_success_rate = chosen_option["success_rate"]
    adjusted_success_rate = base_success_rate * (
        stat_value / 10
    )  # Normalisation sur une base de 10

    # Lancer un dé si le taux de réussite ajusté est bas
    dice_roll = None
    if adjusted_success_rate < 0.5:  # Seuil pour lancer un dé
        roll = random.randint(1, 20)
        success = (
            roll >= (1 - adjusted_success_rate) * 20
        )  # Plus le taux est bas, plus il faut un bon jet
        dice_roll = {
            "roll": roll,
            "success": success,
            "narration": f"Jet de d20: {roll}/20. {'Réussi!' if success else 'Échec...'}",
        }
        if not success:
            # En cas d'échec, appliquer une pénalité (ex: perte de PV)
            if "health_point_change" in chosen_option:
                chosen_option["health_point_change"] *= (
                    2  # Double la pénalité en cas d'échec
                )

    # Appliquer les multiplicateurs
    if "health_point_change" in chosen_option:
        hp_change = chosen_option["health_point_change"] * 100
        player.hp = max(0, min(100, player.hp + hp_change))
        logger.debug(f"HP updated: {player.hp} (change: {hp_change})")

    if "mana_point_change" in chosen_option:
        mp_change = chosen_option["mana_point_change"] * 100
        player.mp = max(0, min(100, player.mp + mp_change))
        logger.debug(f"MP updated: {player.mp} (change: {mp_change})")

    # Stocker le résultat du jet de dé dans l'historique
    last_action["chosen_option"] = option_id
    last_action["dice_roll"] = dice_roll
    last_action["adjusted_success_rate"] = adjusted_success_rate
    last_action["stat_used"] = chosen_option["related_stat"]
    last_action["stat_value"] = stat_value

    game.last_updated = datetime.utcnow()

    return game


# Ajoutez un nouvel endpoint pour obtenir le résultat du dernier jet de dé
@app.get("/games/{game_id}/last_roll", response_model=Optional[DiceRoll])
async def get_last_roll(game_id: str):
    game = GAMES.get(game_id)
    if not game or not game.history:
        return None

    last_action = game.history[-1]
    if "dice_roll" not in last_action:
        return None

    return last_action["dice_roll"]
