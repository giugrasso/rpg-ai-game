from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.db import get_session

router = APIRouter()

# === Gamemaster Routes ===


@router.get("/aimodels", response_model=list[models.AIModels])
async def get_gamemasters(db: AsyncSession = Depends(get_session)):
    return await crud.get_gamemasters(db)


@router.post("/aimodel", response_model=models.AIModels, status_code=201)
async def set_gamemaster(
    game: models.AIModels, db: AsyncSession = Depends(get_session)
):
    return await crud.create_gamemaster(db, game)


@router.get("/aimodel/{gamemaster_id}", response_model=models.AIModels)
async def get_gamemaster(gamemaster_id: int, db: AsyncSession = Depends(get_session)):
    gamemaster = await crud.get_gamemaster(db, gamemaster_id)
    if not gamemaster:
        raise HTTPException(status_code=404, detail="Gamemaster not found")
    return gamemaster


@router.delete("/aimodel/{gamemaster_id}", status_code=204)
async def delete_gamemaster(
    gamemaster_id: int, db: AsyncSession = Depends(get_session)
):
    gamemaster = await crud.get_gamemaster(db, gamemaster_id)
    if not gamemaster:
        raise HTTPException(status_code=404, detail="Gamemaster not found")
    await crud.delete_gamemaster(db, gamemaster)
    return None
