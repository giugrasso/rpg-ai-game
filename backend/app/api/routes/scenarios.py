from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud
from app.core.db import get_session
from app.models import Scenario, ScenarioSchema

router = APIRouter()


@router.get("/scenarios/", response_model=list[Scenario])
async def get_scenarios(db: AsyncSession = Depends(get_session)):
    return await crud.get_scenarios(db)


@router.post("/scenario/", response_model=Scenario, status_code=201)
async def create_scenario(
    scenario_data: ScenarioSchema, db: AsyncSession = Depends(get_session)
):
    # Vérifier si le scénario existe déjà
    existing = await crud.is_scenario_name_existing(db, scenario_data.name)
    if existing:
        raise HTTPException(
            status_code=400, detail="Scenario with this name already exists"
        )

    # Créer le scénario
    scenario = Scenario(
        name=scenario_data.name,
        description=scenario_data.description,
        objectives=scenario_data.objectives,
        mode=scenario_data.mode,
        max_players=scenario_data.max_players,
        context=scenario_data.context,
    )

    await crud.create_scenario(db, scenario)
    await crud.add_roles_to_scenario(db, scenario.id, scenario_data.roles)

    return scenario


@router.get("/scenario/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_session)):
    scenario = await crud.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/scenario/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_session)):
    scenario = await crud.get_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    await crud.delete_scenario(db, scenario)
    return None
