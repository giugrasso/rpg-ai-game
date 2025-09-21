from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, field_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


# === Database models ===
class AIModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    base: str
    system_prompt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    installed: bool = Field(default=False)


# --- Scenario and Game Models ---


class GameMode(str, Enum):
    PVE = "PvE"
    PVP = "PvP"


class Scenario(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    description: str
    objectives: str
    mode: GameMode
    max_players: int
    context: str

    roles: List["CharacterRoleSQL"] = Relationship(back_populates="scenario")


class CharacterRoleSQL(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    scenario_id: str = Field(foreign_key="scenario.id")
    name: str
    stats: Dict[str, int] = Field(sa_column=Column(JSON))
    description: Optional[str] = None

    scenario: Scenario = Relationship(back_populates="roles")


class Character(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    display_name: str
    role: str
    stats: Dict[str, int] = Field(sa_column=Column(JSON))  # stats en JSON
    hp: float
    mp: float
    position: Optional[str] = "start"
    game_id: str = Field(foreign_key="game.id")

    # Relation inverse vers Game
    game: Optional["Game"] = Relationship(back_populates="characters")


class History(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    game_id: str = Field(foreign_key="game.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    player_id: Optional[str] = None  # qui a fait l'action
    action_type: str  # ex: "attack", "move", "heal"
    action_payload: Dict = Field(sa_column=Column(JSON))  # détails de l'action

    game: "Game" = Relationship(back_populates="history_entries")


class Game(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    scenario_id: str
    turn: int = 0
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    characters: List[Character] = Relationship(back_populates="game")
    history_entries: List[History] = Relationship(back_populates="game")


# === Pydantic models (for request/response) ===

# === You can add more models as needed ===


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
