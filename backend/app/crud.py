from typing import List, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel, select

from app.core.config import settings
from app.models import (
    AIModel,
    CharacterRoleSchema,
    Game,
    Player,
    Scenario,
    ScenarioRole,
)

# === Database management ===


async def destroy_db():
    """Destroy all tables in the database."""

    engine = create_async_engine(
        str(settings.SQLALCHEMY_DATABASE_URI),
        echo=True,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


# === Gamemaster CRUD operations ===


async def get_gamemasters(db: AsyncSession):
    """Retrieve all gamemasters from the database."""
    result = await db.execute(select(AIModel))
    return result.scalars().all()


async def create_gamemaster(db: AsyncSession, gamemaster: AIModel) -> AIModel:
    """Create a new gamemaster in the database."""
    db.add(gamemaster)
    await db.commit()
    await db.refresh(gamemaster)
    return gamemaster


async def get_gamemaster(db: AsyncSession, gamemaster_id: int) -> AIModel | None:
    """Retrieve a gamemaster by its ID."""
    result = await db.execute(select(AIModel).where(AIModel.id == gamemaster_id))
    return result.scalars().first()


async def delete_gamemaster(db: AsyncSession, gamemaster: AIModel) -> None:
    """Delete a gamemaster from the database."""
    await db.delete(gamemaster)
    await db.commit()


# === Scenario CRUD operations ===


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


async def get_scenario(db: AsyncSession, scenario_id: UUID) -> Scenario | None:
    """Retrieve a scenario by its ID."""
    result = await db.execute(
        select(Scenario)
        .where(Scenario.id == scenario_id)
        .options(selectinload(Scenario.roles))  # type: ignore
    )
    return result.scalars().first()


async def delete_scenario(db: AsyncSession, scenario: Scenario) -> None:
    """Delete a scenario from the database."""
    await db.delete(scenario)
    await db.commit()


# === Game CRUD operations ===


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


async def get_game(db: AsyncSession, game_id: UUID) -> Game | None:
    """Retrieve a game by its ID."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.scenario))  # type: ignore
    )
    return result.scalars().first()


async def delete_game(db: AsyncSession, game: Game) -> None:
    """Delete a game from the database."""
    await db.delete(game)
    await db.commit()


# === Player CRUD operations ===


async def get_players(db: AsyncSession) -> Sequence[Player]:
    """Retrieve all players with their games."""
    result = await db.execute(
        select(Player).options(selectinload(Player.game))  # type: ignore
    )
    return result.scalars().all()


async def create_player(db: AsyncSession, player: Player) -> Player:
    """Create a new player in the database."""
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player


async def get_player(db: AsyncSession, player_id: UUID) -> Player | None:
    """Retrieve a player by its ID."""
    result = await db.execute(
        select(Player).where(Player.id == player_id).options(selectinload(Player.game))  # type: ignore
    )
    return result.scalars().first()


async def delete_player(db: AsyncSession, player: Player) -> None:
    """Delete a player from the database."""
    await db.delete(player)
    await db.commit()
