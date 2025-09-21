from app import models  # noqa: F401
from app.core.config import settings
from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
