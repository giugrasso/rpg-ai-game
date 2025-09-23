from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import crud
from app.core.db import get_session
from app.models import Scenarios, ScenarioSchema

router = APIRouter()

@router.get("/scenarios/", response_model=list[ScenarioSchema])
def get_scenarios(db: Session = Depends(get_session)):
    return crud.get_scenarios(db)


@router.post(
    "/scenarios/", response_model=ScenarioSchema, status_code=status.HTTP_201_CREATED
)
def create_scenario(scenario_data: ScenarioSchema, db: Session = Depends(get_session)):
    # Vérifier si le scénario existe déjà
    existing = crud.is_scenario_name_existing(db, scenario_data.name)
    if existing:
        raise HTTPException(
            status_code=400, detail="Scenario with this name already exists"
        )

    # Créer le scénario
    scenario = Scenarios(
        name=scenario_data.name,
        description=scenario_data.description,
        objectives=scenario_data.objectives,
        mode=scenario_data.mode,
        max_players=scenario_data.max_players,
        context=scenario_data.context,
    )

    crud.create_scenario(db, scenario)

    # Ajouter les rôles
    crud.add_roles_to_scenario(db, scenario.id, scenario_data.roles)

    return scenario_data
