from typing import Optional

from fastapi import Depends, Request, exceptions
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, schemas, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    JWTStrategy, CookieTransport,
)

from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db import get_async_session
from db.models import User, get_user_db


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    __secret = get_settings().SECRET
    reset_password_token_secret = __secret
    verification_token_secret = __secret

    async def create(
            self,
            user_create: schemas.UC,
            safe: bool = False,
            request: Optional[Request] = None,
            session: AsyncSession = Depends(get_async_session)
    ) -> models.UP:
        statement = select(User).where(User.username == user_create.username)

        if (await self.user_db.session.execute(statement)).first() is not None:
            raise exceptions.HTTPException(400, detail='REGISTER_USER_ALREADY_EXISTS')
        return await super().create(user_create, safe, request)

    async def on_after_register(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        await self.request_verify(user)
        await super().on_after_register(user)

    async def authenticate(
            self, credentials: OAuth2PasswordRequestForm
    ) -> Optional[models.UP]:
        user = await self.user_db.get_by_email(credentials.username)
        if user is None:
            statement = select(User).where(User.username == credentials.username)
            user = (await self.user_db.session.execute(statement)).first()
            if user is None:
                return None
            credentials.username = user[0].email
        return await super().authenticate(credentials)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(cookie_max_age=3600, cookie_samesite='none', cookie_httponly=False)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=get_settings().SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
