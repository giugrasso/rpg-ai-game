from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.db import get_session

router = APIRouter()

@router.get("/games", response_model=list[models.Game])
async def get_games(db: AsyncSession = Depends(get_session)):
    return await crud.get_games(db)

@router.post("/game", response_model=models.GameSchema, status_code=201)
async def create_game(
    game: models.GameSchema, db: AsyncSession = Depends(get_session)
):
    game_obj = models.Game(
        scenario_id=game.scenario_id,
        turn=game.turn,
        active=game.active

    )
    await crud.create_game(db, game_obj)
    return game_obj
