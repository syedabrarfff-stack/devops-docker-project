from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.operations.capabilities import capability_status


router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    return await capability_status(db)
