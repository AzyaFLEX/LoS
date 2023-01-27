import os

from fastapi import UploadFile, HTTPException

from config import get_settings


async def save_file(file: UploadFile, file_path: str):
    settings = get_settings()

    try:
        with open(file_path, 'wb') as new_file:
            counter = 0
            while content := await file.read(1024 * 1024):
                counter += 1
                if counter > settings.MAX_FILE_SIZE:
                    raise Exception(f'file size more than {settings.MAX_FILE_SIZE} Mb')
                new_file.write(content)

    except Exception as error:
        os.remove(file_path)
        raise HTTPException(500, detail=f'saving image error: {error}')

    return file_path
