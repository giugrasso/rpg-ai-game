from fastapi import FastAPI

from app.api.routes import config, games, scenarios
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


app.include_router(config.router, prefix="/config", tags=["config"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
app.include_router(games.router, prefix="/games", tags=["games"])
