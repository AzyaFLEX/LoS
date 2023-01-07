from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import Base
from db.engine import get_async_session


class User(SQLAlchemyBaseUserTable, Base):
    __tablename__ = 'user'

    username = Column(String(30), index=True, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    first_name = Column(String(30), nullable=False)
    second_name = Column(String(30), nullable=False)


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
