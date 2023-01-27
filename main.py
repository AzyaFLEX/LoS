from multiprocessing import Process, Queue

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from config import get_settings
from controllers.user_controller import fastapi_users, auth_backend
from processes import __all__ as all_processes
from processes.processes_manager import get_processes_manager
from routers import __all__ as routers
from routers.schemas import UserRead, UserCreate, UserUpdate


def get_application(settings) -> FastAPI:
    origins = [
        'https://legacyofsothorys.ru'
    ]

    application = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        version=settings.VERSION,
        description='LoS | Minecraft Project'
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH"],  # remove "OPTIONS"
        allow_headers=["Content-Type", "Set-Cookie"],
    )

    application.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/auth",
        tags=["auth"],
    )

    application.include_router(
        fastapi_users.get_auth_router(auth_backend),
        prefix="/auth/jwt",
        tags=["auth"],
    )

    application.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix="/auth",
        tags=["auth"],
    )

    application.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )

    for router in routers:
        application.include_router(router)

    add_pagination(application)

    return application


def run_application(settings):
    app = get_application(settings)

    server_data = {
        'host': settings.SERVER_HOST,
        'port': settings.SERVER_PORT
    }

    if not settings.DEBUG:
        server_data.update(settings.SSL_DATA)

    uvicorn.run(app, **server_data)


if __name__ == '__main__':
    queue = Queue()
    processes_manager = get_processes_manager()
    processes_manager.VK_PROCESS_QUEUE = queue

    for process in all_processes:
        new_process = Process(target=process, args=(queue, ))
        new_process.start()

    run_application(get_settings())
