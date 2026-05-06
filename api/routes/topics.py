from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import Topic
from shared.models import TopicResponse

router = APIRouter()


@router.get("/", response_model=list[TopicResponse])
async def get_topics(db: Annotated[AsyncSession, Depends(get_db)]) -> list[TopicResponse]:
    """Get all topics ordered alphabetically."""
    result = await db.execute(select(Topic).order_by(Topic.name))
    topics = result.scalars().all()
    return list(topics)
