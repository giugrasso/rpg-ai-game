from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import crud, models
from app.core.db import get_session

router = APIRouter()

@router.get("/aimodel", response_model=list[models.AIModel])
def get_gamemasters(db: Session = Depends(get_session)):
    return crud.get_gamemasters(db)

@router.post("/aimodel", response_model=models.AIModel)
def set_gamemaster(game: models.AIModel, db: Session = Depends(get_session)):
    return crud.create_gamemaster(db, game)
