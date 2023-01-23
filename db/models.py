import datetime

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Boolean, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, declarative_mixin
from sqlalchemy.sql import expression

from db import Base
from db.engine import get_async_session


@declarative_mixin
class TimestampMixin:
    """Mixin with timestamp fields"""
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=datetime.datetime.now
    )


class User(TimestampMixin, SQLAlchemyBaseUserTable, Base):
    __tablename__ = 'user'

    username = Column(String(30), index=True, unique=True, nullable=False)

    first_name = Column(String(30), nullable=False)
    second_name = Column(String(30), nullable=False)

    news = relationship('News', back_populates='author', order_by='News.created_at.desc()')
    comments = relationship('Comment', back_populates='author', order_by='Comment.created_at.desc()')


class News(TimestampMixin, Base):
    __tablename__ = 'news'

    title = Column(String(64), nullable=False)
    context = Column(String(2048), nullable=False)
    author_id = Column(ForeignKey('user.id'), nullable=False, unique=False)

    comments = relationship('Comment', lazy='selectin')
    rating = relationship('NewsRating', lazy='selectin')

    author = relationship('User', back_populates='news', uselist=False)
    file = relationship('NewsFile', back_populates='news', uselist=False)


class Comment(TimestampMixin, Base):
    __tablename__ = 'comment'

    news_id = Column(ForeignKey('news.id'), nullable=False)
    context = Column(String(1024), nullable=False)
    author_id = Column(ForeignKey('user.id'), nullable=False)

    author = relationship('User', back_populates='comments')


class NewsRating(Base):
    __tablename__ = 'news_rating'

    user_id = Column(ForeignKey('user.id'), index=True, nullable=False)
    news_id = Column(ForeignKey('news.id'), index=True, nullable=False)

    positive = Column(Boolean, server_default=expression.true(), nullable=False)


class NewsFile(Base):
    __tablename__ = 'news_file'

    news_id = Column(ForeignKey('news.id'), index=True, nullable=False, unique=True)
    file_format = Column(String(10), nullable=False)
    file_path = Column(String(1024), nullable=False)

    news = relationship('News', back_populates='file')


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
