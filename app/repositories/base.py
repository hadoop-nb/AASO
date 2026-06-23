from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import inspect, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


def _get_pk_column(model: type[Base]):
    mapper = inspect(model)
    return mapper.primary_key[0]


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model
        self.pk_column = _get_pk_column(model)

    async def create(self, data: dict[str, Any]) -> ModelT:
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, id: str) -> ModelT | None:
        stmt = select(self.model).where(self.pk_column == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, id: str, data: dict[str, Any]
    ) -> ModelT | None:
        stmt = (
            update(self.model)
            .where(self.pk_column == id)
            .values(**data)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: str) -> bool:
        stmt = delete(self.model).where(self.pk_column == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ModelT]:
        stmt = select(self.model)
        if filters:
            for key, value in filters.items():
                column = getattr(self.model, key, None)
                if column is not None:
                    stmt = stmt.where(column == value)
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
