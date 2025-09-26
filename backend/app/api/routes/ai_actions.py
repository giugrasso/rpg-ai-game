from uuid import UUID

from fastapi import APIRouter
from ollama import AsyncClient

from app.core.config import settings
from app.models import AIWelcomeResponseSchema

router = APIRouter()


@router.post(
    "/ai_action",
    response_model=AIWelcomeResponseSchema,
)
async def ai_action(
    game_id: UUID,
):
    client = AsyncClient(host=settings.OLLAMA_SERVER)
    response = await client.chat(
        model="game_master",
        messages=[
            {
                "role": "user",
                "content": """Le jeu commence.""",
            },
        ],
        stream=False,
    )

    return AIWelcomeResponseSchema(
        welcome_message=response["message"]["content"],
        scenario_description="A définir",
        player_roles=[],
    )
