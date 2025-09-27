from datetime import datetime
from datetime import timezone as tz
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, field_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


# === Database models ===
class AIModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    base: str
    system_prompt: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz.utc))
    installed: bool = Field(default=False)


# --- Scenario and Game Models ---


class GameMode(str, Enum):
    PVE = "PvE"
    PVP = "PvP"


class Scenario(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: str
    objectives: str
    mode: GameMode
    max_players: int
    context: str

    # Relations
    roles: List["ScenarioRole"] = Relationship(back_populates="scenario")
    games: List["Game"] = Relationship(back_populates="scenario")


class ScenarioRole(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scenario_id: Optional[UUID] = Field(foreign_key="scenario.id")
    name: str
    stats: Dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    description: Optional[str] = None

    # Relations
    scenario: Optional[Scenario] = Relationship(back_populates="roles")


class Phase(str, Enum):
    AI = "AI"
    PLAYER = "PLAYER"


class Game(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    scenario_id: UUID = Field(foreign_key="scenario.id")
    turn: int = 0
    active: bool = True
    current_player_id: Optional[UUID] = None
    phase: Phase = Field(default=Phase.AI)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(tz.utc))

    # Relations
    scenario: Optional[Scenario] = Relationship(back_populates="games")
    players: List["Player"] = Relationship(back_populates="game")
    history_entries: List["History"] = Relationship(back_populates="game")


class Player(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    display_name: str
    role: str
    initiative: int = 0
    order: int = 0
    alive: bool = True
    stats: Dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON))
    hp: float
    mp: float
    position: str = Field(default="start")
    game_id: UUID = Field(foreign_key="game.id")

    # Relations
    game: Optional[Game] = Relationship(back_populates="players")
    history_entries: List["History"] = Relationship(back_populates="player")


class History(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    game_id: UUID = Field(foreign_key="game.id")
    player_id: Optional[UUID] = Field(default=None, foreign_key="player.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz.utc))
    action_type: str  # ex: "attack", "move", "heal"
    action_payload: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    success: Optional[bool] = None
    result: Dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Relations
    game: Game = Relationship(back_populates="history_entries")
    player: Optional[Player] = Relationship(back_populates="history_entries")


# === Pydantic models (for request/response) ===


class CharacterRoleSchema(BaseModel):
    name: str
    stats: Dict[str, int]
    description: str | None = None


class ScenarioSchema(BaseModel):
    name: str
    description: str
    objectives: str
    mode: GameMode
    max_players: int
    context: str
    roles: List[CharacterRoleSchema]


class Option(BaseModel):
    id: int
    description: str
    success_rate: float = Field(ge=0.0, le=1.0)  # estimated success rate (0.0 to 1.0)
    health_point_change: float = Field(ge=-1.0, le=1.0)
    mana_point_change: float = Field(ge=-1.0, le=1.0)
    related_stat: str  # e.g. "force", "intelligence", etc.


class AIResponseValidator(BaseModel):
    narration: str
    options: List[Option] = []

    @field_validator("options", mode="before")
    def validate_options(cls, v):
        if v is None:
            return []
        return v


class GameSchema(BaseModel):
    scenario_id: UUID
    turn: int = 0
    active: bool = True
