from fastapi import APIRouter

from app import crud

router = APIRouter()

# === Database Management Routes ===


@router.delete(
    "/dbdestroy",
    status_code=204,
    summary="Destroy all tables in the database",
    description="For development ONLY. This will delete all data and tables in the database. Use with caution.",
    name="Destroy Database",
)
async def destroy_db():
    await crud.destroy_db()
