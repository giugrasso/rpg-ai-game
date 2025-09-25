from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.db import get_session

router = APIRouter()

@router.get("/players", response_model=list[models.Player])
async def get_players(db: AsyncSession = Depends(get_session)):
    return await crud.get_players(db)

@router.post("/player", response_model=models.Player, status_code=201)
async def create_player(
    player: models.Player, db: AsyncSession = Depends(get_session)
):
    player_obj = models.Player(
        display_name=player.display_name,
        role=player.role,
        stats=player.stats,
        hp=player.hp,
        mp=player.mp,
        position=player.position,
        game_id=player.game_id,
    )
    await crud.create_player(db, player_obj)
    return player_obj

@router.get("/player/{player_id}", response_model=models.Player)
async def get_player(player_id: UUID, db: AsyncSession = Depends(get_session)):
    player = await crud.get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.delete("/player/{player_id}", status_code=204)
async def delete_player(player_id: UUID, db: AsyncSession = Depends(get_session)):
    player = await crud.get_player(db, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await crud.delete_player(db, player)
    return None
