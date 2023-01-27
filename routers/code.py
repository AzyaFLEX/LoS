import base64
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from config import get_settings
from controllers.files_controller import FileController
from controllers.saving_files import save_file
from controllers.user_controller import current_active_user
from db import get_async_session, CodeFile, User

router = APIRouter(
    prefix="/code",
    tags=["code"],
)


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
