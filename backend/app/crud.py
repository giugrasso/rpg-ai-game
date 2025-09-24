from sqlmodel import Session, select

from app.models import AIModels, Scenario, ScenarioRole


def get_gamemasters(db: Session):
    """Retrieve all gamemasters from the database."""
    return db.exec(select(AIModels)).all()


def create_gamemaster(db: Session, gamemaster: AIModels) -> AIModels:
    """Create a new gamemaster in the database."""
    db.add(gamemaster)
    db.commit()
    db.refresh(gamemaster)
    return gamemaster


def get_scenarios(db: Session):
    scenarios = db.exec(select(Scenario)).all()
    # Chaque scénario aura son .roles accessible grâce à Relationship
    for scenario in scenarios:
        _ = scenario.roles  # Trigger lazy load si nécessaire
    return scenarios


def is_scenario_name_existing(db: Session, name: str) -> bool:
    """Check if a scenario with the given name already exists."""
    existing = db.exec(select(Scenario).where(Scenario.name == name)).first()
    return existing is not None


def create_scenario(db: Session, scenario: Scenario) -> Scenario:
    """Create a new scenario in the database."""
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def add_roles_to_scenario(db: Session, scenario_id: str, roles: list):
    """Add roles to a scenario."""
    for role_data in roles:
        role = ScenarioRole(
            scenario_id=scenario_id,
            name=role_data.name,
            stats=role_data.stats,
            description=role_data.description,
        )
        db.add(role)
    db.commit()
    return roles
