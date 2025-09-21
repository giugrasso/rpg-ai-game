
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel


# === Database models ===
class AIModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    base: str
    system_prompt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    installed: bool = Field(default=False)

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