from sqlalchemy.orm import as_declarative
from sqlalchemy import Column, Integer


@as_declarative()
class Base:
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
