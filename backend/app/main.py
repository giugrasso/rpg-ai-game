import logging

from fastapi import FastAPI

from app.api.routes import config
from app.core.db import init_db
from app.initial_data import initial_data

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()

    initial_data()


app.include_router(config.router, prefix="/config", tags=["config"])
