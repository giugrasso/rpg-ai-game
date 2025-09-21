from fastapi import FastAPI

from app.api.routes import config
from app.core.db import init_db
from app.initial_data import initial_data

from .logging_config import logger

app = FastAPI()


@app.on_event("startup")
def on_startup():
    logger.info("Starting up...")

    logger.info("Initializing database...")
    init_db()

    logger.info("Inserting initial data...")
    initial_data()


app.include_router(config.router, prefix="/config", tags=["config"])
