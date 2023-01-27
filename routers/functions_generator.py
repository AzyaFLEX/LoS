from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams
from fastapi_pagination.ext.async_sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from controllers.user_controller import current_active_user
from db import Base, get_async_session, User


class BaseFunctionGenerator:
    @staticmethod
    def get_by_id(router: APIRouter, sql_class: Base, response_scheme: BaseModel):
        @router.get(f'/{sql_class.__name__}/by_id/' + '{object_id}', response_model=response_scheme)
        async def get_function(object_id: int, session: AsyncSession = Depends(get_async_session)):
            data: sql_class | None = await session.get(sql_class, object_id)

            if data is None:
                raise HTTPException(404, detail='data not found')

            return response_scheme.from_orm(data)

    @staticmethod
    def patch_by_id(router: APIRouter, sql_class: Base, options: tuple,
                    path_scheme: BaseModel, response_scheme: BaseModel, secure=True):
        @router.patch(f'/{sql_class.__name__}/' + '{object_id}', response_model=response_scheme)
        async def patch_function(object_id: int, patch_data: path_scheme.__class__,
                                   session: AsyncSession = Depends(get_async_session),
                                   current_user: User | None = (Depends(current_active_user) if secure else None)):
            if secure:
                if not current_user.is_superuser:
                    raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

            data: sql_class | None = await session.get(sql_class, object_id, options=options)

            if data is None:
                raise HTTPException(404, detail=f'no {sql_class.__name__} with id {object_id}')

            to_patch = patch_data.dict()
            for key in to_patch:
                setattr(data, key, to_patch[key])

            session.add(data)
            await session.commit()
            await session.refresh(data)

            return response_scheme.from_orm(data)

    @staticmethod
    def delete_by_od(router: APIRouter, sql_class: Base, options: tuple, secure=True):
        @router.delete(f'{sql_class.__name__}/' + '{object_id}', status_code=204)
        async def delete_function(object_id: int, session: AsyncSession = Depends(get_async_session),
                                  current_user: User = (Depends(current_active_user) if secure else None)):
            if not current_user.is_superuser:
                raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

            data: sql_class | None = await session.get(sql_class, object_id, options=options)

            if data is None:
                raise HTTPException(404, detail=f'no {sql_class.__name__} with id {object_id}')

            await session.delete(data)

    @staticmethod
    def get_all_by_response(router: APIRouter, response_scheme: BaseModel, request: Select):
        @router.get(f'/{request.column_descriptions[0]["expr"].__name__}/all',
                    response_model=LimitOffsetPage[response_scheme])
        async def get_all_news(limit: int = Query(default=50, lt=101, gt=0),
                               offset: int = Query(default=0, gt=-1),
                               session: AsyncSession = Depends(get_async_session)):
            params = LimitOffsetParams(limit=limit, offset=offset)

            data = await paginate(session, request, params=params)

            return data
