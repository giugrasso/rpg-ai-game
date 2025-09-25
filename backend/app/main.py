from fastapi import FastAPI

from app.api.routes import admin, aimodels, games, players, scenarios
from app.core.db import init_db
from app.initial_data import init_first_scenario, init_game_master

from .logging_config import logger

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    logger.info("Starting up...")

    logger.info("Initializing database...")
    await init_db()

    logger.info("Inserting initial data...")
    await init_game_master()

    logger.info("Inserting initial scenario...")
    await init_first_scenario()


app.include_router(admin.router, prefix="/v1", tags=["admin"])
app.include_router(aimodels.router, prefix="/v1", tags=["aimodels"])
app.include_router(scenarios.router, prefix="/v1", tags=["scenarios"])
app.include_router(games.router, prefix="/v1", tags=["games"])
app.include_router(players.router, prefix="/v1", tags=["players"])
