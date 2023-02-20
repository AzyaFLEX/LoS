import base64
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import FileResponse

from config import get_settings
from controllers.files_controller import FileController
from controllers.saving_files import save_file
from controllers.user_controller import current_active_user
from db import get_async_session, CodeFile, User, CodeCharacter, CodeFraction, CodeLocation, CodeItem, CodeDifferent, \
    Base, CodeFileClass
from routers.schemas import CodeCharacterRead, CodeCharacterPatch, CodeFractionRead, CodeFractionPatch, \
    CodeLocationRead, CodeLocationPatch, CodeItemRead, CodeItemPatch, CodeDifferentRead, CodeDifferentPatch, \
    BaseModelsPostWithFile, CodeDifferentGet, CodeItemGet, CodeLocationGet, CodeFractionGet

router = APIRouter(
    prefix="/code",
    tags=["code"],
)

sql_classes = {
    CodeCharacter: {
        'get': CodeCharacterRead,
        'post': CodeCharacterRead,
        'patch': CodeCharacterPatch,
    },

    CodeFraction: {
        'get': CodeFractionRead,
        'post': CodeFractionGet,
        'patch': CodeFractionPatch,
    },

    CodeLocation: {
        'get': CodeLocationRead,
        'post': CodeLocationGet,
        'patch': CodeLocationPatch,
    },

    CodeItem: {
        'get': CodeItemRead,
        'post': CodeItemGet,
        'patch': CodeItemPatch,
    },

    CodeDifferent: {
        'get': CodeDifferentRead,
        'post': CodeDifferentGet,
        'patch': CodeDifferentPatch,
    }
}


def get_function(sql_class: CodeFileClass, response_scheme: BaseModel) -> None:
    @router.get(f'/{sql_class.__name__}/' + '{object_id}', response_model=response_scheme)
    async def function(object_id: int, session: AsyncSession = Depends(get_async_session)):
        data: sql_class | None = await session.get(sql_class, object_id, options=(selectinload(sql_class.code_file), ))

        if data is None:
            raise HTTPException(404, detail='data not found')

        return response_scheme.from_orm(data)


async def saving_file(_file: UploadFile, session: AsyncSession):
    settings = get_settings()
    filepath = settings.CODE_IMAGE_CONTROLLER.get_filename()

    try:
        with open(filepath, 'wb') as to_save_file:
            counter = 0
            while content := await _file.read(1024 * 1024):
                counter += 1
                if counter > settings.MAX_FILE_SIZE:
                    to_save_file.close()
                    os.remove(filepath)
                    raise HTTPException(400, detail=f'file size more than {settings.MAX_FILE_SIZE} Mb')
                to_save_file.write(content)

    except Exception as error:
        os.remove(filepath)
        raise HTTPException(500, detail=f'saving image error: {error}')

    _file = CodeFile(file_format=settings.CODE_IMAGE_CONTROLLER.file_format, file_path=filepath)
    session.add(_file)
    await session.commit()
    await session.refresh(_file)
    return _file


def post_function(sql_class: Base, get_scheme: BaseModelsPostWithFile, response_scheme: BaseModel) -> None:
    @router.post(f'/{sql_class.__name__}', response_model=response_scheme)
    async def function(file: UploadFile, post_data: get_scheme = Body(...),
                       session: AsyncSession = Depends(get_async_session),
                       current_user: User = Depends(current_active_user)):

        if not current_user.is_superuser:
            raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

        data_model: sql_class = sql_class(**post_data.dict())

        file_model: CodeFile = await saving_file(file, session)

        data_model.code_file_id = file_model.id

        session.add(data_model)
        await session.commit()
        await session.refresh(data_model)
        return response_scheme.from_orm(data_model)


# Шашлички из курицы и еживичный твист
def patch_function(sql_class: CodeFileClass, get_scheme: BaseModelsPostWithFile, response_scheme: BaseModel) -> None:
    @router.patch(f'{sql_class.__name__}' + '{object_id}', response_model=response_scheme)
    async def function(object_id: int,
                       file: UploadFile | None = None, post_data: get_scheme | None = Body(default=None),
                       session: AsyncSession = Depends(get_async_session),
                       current_user: User = Depends(current_active_user)):
        if not current_user.is_superuser:
            raise HTTPException(403, detail='Access Denied')

        data: sql_class = await session.get(sql_class, object_id)

        if data is None:
            raise HTTPException(404, detail=f'{sql_class.__name__} {object_id} not found')

        if file is not None:
            data.code_file_id = (await saving_file(file, session)).id

        if post_data is not None:
            for key in post_data.dict():
                setattr(data, key, post_data.dict()[key])

        session.add(data)
        await session.commit()
        await session.refresh(data)

        data.code_file = await session.get(CodeFile, data.code_file_id)
        return response_scheme.from_orm(data)


def delete_function(sql_class: CodeFileClass) -> None:
    @router.delete(f'/{sql_class.__name__}/' + '{object_id}', status_code=203)
    async def function(object_id: int, session: AsyncSession = Depends(get_async_session),
                       current_user: User = Depends(current_active_user)):
        if not current_user.is_superuser:
            raise HTTPException(403, detail='Access Denied')

        data: sql_class | None = await session.get(sql_class, object_id, options=(selectinload(sql_class.code_file), ))

        if data is None:
            raise HTTPException(404, detail='data not found')

        if os.path.isfile(data.code_file.file_path):
            os.remove(data.code_file.file_path)

        await session.delete(data.code_file)
        await session.delete(data)


@router.get('/files/{file_id}')
async def get_file_by_id(file_id: int, session: AsyncSession = Depends(get_async_session)):
    image: CodeFile | None = await session.get(CodeFile, file_id)

    if image is None:
        raise HTTPException(404, detail=f'no image {file_id} found')

    if not os.path.isfile(image.file_path):
        raise HTTPException(404, detail=f'server founded news file in db but miss {image.file_path}')

    return FileResponse(image.file_path)


@router.get('/files/base64/{file_id}')
async def get_file_by_id_base64(file_id: int, session: AsyncSession = Depends(get_async_session)):
    image: CodeFile | None = await session.get(CodeFile, file_id)

    if image is None:
        raise HTTPException(404, detail=f'server miss news {file_id} files')

    try:
        with open(image.file_path, 'rb') as file_content:
            content: str = base64.b64encode(file_content.read())
    except FileNotFoundError:
        raise HTTPException(500, detail=f'server founded news file in db but miss {image.file_path}')

    return content


@router.post('/files/', status_code=203)
async def post_image(file: UploadFile = File(...),
                     session: AsyncSession = Depends(get_async_session),
                     current_user: User = Depends(current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

    file_controller: FileController = get_settings().CODE_IMAGE_CONTROLLER
    code_file = CodeFile(file_path=await save_file(file, file_controller.get_filename()),
                         file_format=file_controller.file_format)

    session.add(code_file)
    await session.commit()
    await session.refresh(code_file)


for sql_class in sql_classes:
    get_function(sql_class, sql_classes[sql_class]['get'])
    post_function(sql_class, sql_classes[sql_class]['post'], sql_classes[sql_class]['get'])
    patch_function(sql_class, sql_classes[sql_class]['patch'], sql_classes[sql_class]['get'])
    delete_function(sql_class)

