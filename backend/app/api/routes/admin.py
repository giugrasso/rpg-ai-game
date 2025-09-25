from fastapi import APIRouter

from app import crud

router = APIRouter()

# === Database Management Routes ===


@router.delete(
    "/dbdestroy",
    status_code=204,
    summary="Destroy all tables in the database",
    description="This will delete all data and tables in the database. Use with caution.",
)
async def destroy_db():
    await crud.destroy_db()
