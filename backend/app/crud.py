from typing import List, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.models import AIModels, CharacterRoleSchema, Game, Scenario, ScenarioRole


async def get_gamemasters(db: AsyncSession):
    """Retrieve all gamemasters from the database."""
    result = await db.execute(select(AIModels))
    return result.scalars().all()


async def create_gamemaster(db: AsyncSession, gamemaster: AIModels) -> AIModels:
    """Create a new gamemaster in the database."""
    db.add(gamemaster)
    await db.commit()
    await db.refresh(gamemaster)
    return gamemaster


async def get_scenarios(db: AsyncSession):
    """Retrieve all scenarios with their roles."""
    result = await db.execute(
        select(Scenario).options(selectinload(Scenario.roles))  # type: ignore
    )
    scenarios = result.scalars().all()
    return scenarios


async def is_scenario_name_existing(db: AsyncSession, name: str) -> bool:
    """Check if a scenario with the given name already exists."""
    result = await db.execute(select(Scenario).where(Scenario.name == name))
    scenario = result.scalars().first()
    return scenario is not None


async def create_scenario(db: AsyncSession, scenario: Scenario) -> Scenario:
    """Create a new scenario in the database."""
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def add_roles_to_scenario(
    db: AsyncSession, scenario_id: UUID, roles: List[CharacterRoleSchema]
) -> List["ScenarioRole"]:
    """Add roles to a scenario and return the created roles."""
    created_roles: List["ScenarioRole"] = []

    try:
        for role_data in roles:
            role = ScenarioRole(
                scenario_id=scenario_id,
                name=role_data.name,
                stats=role_data.stats,
                description=role_data.description,
            )
            db.add(role)
            created_roles.append(role)

        await db.commit()

        # Recharge les IDs générés en DB
        for role in created_roles:
            await db.refresh(role)

    except Exception:
        await db.rollback()
        raise

    return created_roles

async def get_games(db: AsyncSession) -> Sequence[Game]:
    """Retrieve all games with their scenarios."""
    result = await db.execute(
        select(Game).options(selectinload(Game.scenario))  # type: ignore
    )
    return result.scalars().all()

async def create_game(db: AsyncSession, game: Game) -> Game:
    """Create a new game in the database."""
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game
