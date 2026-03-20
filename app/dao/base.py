from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


# Базовый Data Access Object
# Commit DAO не делает, он вызывается в конце эндпоинта
class BaseDAO:
    
    def __init__(self, session: AsyncSession, model) -> None:
        self.session = session
        self.model = model # ORM модель, для которой будем выполнять запросы
    
    async def get_one_or_none(self, **filter_by):
        stmt = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, obj_id: UUID | str):
        return await self.get_one_or_none(id=obj_id)
    
    async def get_all(self, **filter_by):
        stmt = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(stmt)
        return result.scalars()
    
    async def create(self, **data):
        obj = self.model(**data)
        self.session.add(obj)
        return obj
    
    async def delete(self, **filter_by):
        query = delete(self.model).filter_by(**filter_by)
        await self.session.execute(query)
