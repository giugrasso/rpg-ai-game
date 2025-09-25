from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.db import get_session

router = APIRouter()


@router.get("/aimodels", response_model=list[models.AIModels])
async def get_gamemasters(db: AsyncSession = Depends(get_session)):
    return await crud.get_gamemasters(db)


@router.post("/aimodel", response_model=models.AIModels, status_code=201)
async def set_gamemaster(
    game: models.AIModels, db: AsyncSession = Depends(get_session)
):
    return await crud.create_gamemaster(db, game)
