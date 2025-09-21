from sqlmodel import Session, select

from app.models import AIModel


def get_gamemasters(db: Session):
    """Retrieve all gamemasters from the database."""
    return db.exec(select(AIModel)).all()

def create_gamemaster(db: Session, gamemaster: AIModel):
    """Create a new gamemaster in the database."""
    db.add(gamemaster)
    db.commit()
    db.refresh(gamemaster)
    return gamemaster