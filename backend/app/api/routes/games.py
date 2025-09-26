from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.db import get_session

router = APIRouter()


@router.get("/games", response_model=list[models.Game])
async def get_games(db: AsyncSession = Depends(get_session)):
    return await crud.get_games(db)


@router.post("/game", response_model=models.Game, status_code=201)
async def create_game(game: models.GameSchema, db: AsyncSession = Depends(get_session)):
    game_obj = models.Game(
        scenario_id=game.scenario_id,
        turn=game.turn,
        active=game.active,
        current_player_id=None,
    )
    await crud.create_game(db, game_obj)
    return game_obj


@router.get("/game/{game_id}", response_model=models.Game)
async def get_game(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.delete("/game/{game_id}", status_code=204)
async def delete_game(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    await crud.delete_game(db, game)
    return None


@router.post("/game/{game_id}/roll_initiative", response_model=list[models.Player])
async def roll_initiative(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = await crud.get_players_by_game(db, game_id)
    if not players:
        raise HTTPException(status_code=404, detail="No players found for this game")

    import random

    # Roll initiative for each player and assign turn order
    for player in players:
        player.initiative = random.randint(1, 20) + player.stats.get("dexterity", 0)
        await crud.update_player(db, player)

    # Sort players by turn order descending
    players = sorted(players, key=lambda p: p.initiative, reverse=True)

    # Set players' order based on initiative
    for index, player in enumerate(players):
        player.order = index + 1
        await crud.update_player(db, player)

    # Set the current player to the one with the highest initiative
    game.current_player_id = players[0].id
    await crud.update_game(db, game)

    return players
