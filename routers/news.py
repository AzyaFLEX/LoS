import os

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, Body, Query
from fastapi_pagination.limit_offset import LimitOffsetPage, LimitOffsetParams
from fastapi_pagination.ext.async_sqlalchemy import paginate
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import FileResponse

from config import get_settings
from controllers.user_controller import current_active_user
from db import get_async_session, News, Comment, NewsRating, User, NewsFile
from routers.schemas import NewsRead, NewsPostScheme, NewsRatingRead, NewsPatchScheme

router = APIRouter(
    prefix="/news",
    tags=["news"],
)


async def save_file(file: UploadFile):
    settings = get_settings()

    file_path = settings.IMAGE_CONTROLLER.get_filename()

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


@router.get('/by_id/{news_id}/rating')
async def get_news_rating(news_id: int | None = None, session: AsyncSession = Depends(get_async_session),
                          news=Header(None, include_in_schema=False)):
    async def get_output(_news_id):
        rating_objs = (await session.execute(select(NewsRating).where(NewsRating.news_id == _news_id))).scalars().all()
        return sum(map(lambda data_obj: 1 if data_obj.positive else -1, rating_objs))

    news = await session.get(News, news_id) if news is None else news

    if news is None:
        raise HTTPException(404, detail=f'no news with id {news_id}')

    return await get_output(news.id)


@router.patch('/by_id/{news_id}/rating/set/{positive}', response_model=NewsRatingRead)
async def add_news_rating(news_id: int, positive: bool, session: AsyncSession = Depends(get_async_session),
                          current_user: User = Depends(current_active_user)):
    news = await session.get(News, news_id)

    if news is None:
        raise HTTPException(404, detail=f'no news with id {news_id}')

    request = select(NewsRating).where((NewsRating.user_id == current_user.id) & (NewsRating.news_id == news.id))
    rating_data: NewsRating = (await session.execute(request)).scalars().first()

    if rating_data is None:
        rating_data = NewsRating(user_id=current_user.id, news_id=news.id, positive=positive)
    elif rating_data.positive != positive:
        rating_data.positive = positive

    session.add(rating_data)
    await session.commit()
    await session.refresh(rating_data)
    return NewsRatingRead.from_orm(rating_data)


@router.get('/by_id/{news_id}', response_model=NewsRead)
async def get_news_by_id(news_id: int, session: AsyncSession = Depends(get_async_session)):
    news: News = await session.get(News, news_id, options=(
        selectinload(News.comments),
        selectinload(News.author),
        selectinload(News.file),
        selectinload(News.comments, Comment.author),
    ))

    if news is None:
        raise HTTPException(404, detail=f'no news with id {news_id}')

    news.rating_value = await get_news_rating(session=session, news=news)

    return NewsRead.from_orm(news)


@router.get('/all', response_model=LimitOffsetPage[NewsRead])
async def get_all_news(limit: int = Query(default=50, lt=101, gt=0),
                       offset: int = Query(default=0, gt=-1),
                       session: AsyncSession = Depends(get_async_session)):
    params = LimitOffsetParams(limit=limit, offset=offset)

    request = select(News).options(
        selectinload(News.comments),
        selectinload(News.author),
        selectinload(News.comments, Comment.author),
    ).order_by(desc(News.created_at))

    data = await paginate(session, request, params=params)

    for news in data.items:
        news.rating_value = await get_news_rating(session=session, news=news)

    return data


@router.post('/', response_model=NewsRead)
async def post_news(post_data: NewsPostScheme = Body(), file: UploadFile | None = None,
                    session: AsyncSession = Depends(get_async_session),
                    current_user: User = Depends(current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

    news = News(**post_data.dict(), author=current_user)
    session.add(news)
    await session.commit()
    await session.refresh(news)

    if file is not None:
        settings = get_settings()
        file_format = file.filename.split('.')[-1]

        if file_format != settings.IMAGE_CONTROLLER.file_format:
            raise HTTPException(400, detail='wrong image format')

        file_path = await save_file(file)

        file = NewsFile(news_id=news.id, file_format=settings.IMAGE_CONTROLLER.file_format, file_path=file_path)
        session.add(file)
        await session.commit()

        news.rating_value = 0

    return NewsRead.from_orm(news)


@router.get('/{news_id}/image', response_class=FileResponse)
async def get_new_image(news_id: int, session: AsyncSession = Depends(get_async_session)):
    request = select(NewsFile).where(NewsFile.news_id == news_id)
    image: NewsFile | None = (await session.execute(request)).scalars().first()

    if image is None:
        raise HTTPException(404, detail=f'no image found')

    return FileResponse(image.file_path)


@router.patch('/{news_id}', response_model=NewsRead)
async def patch_news_by_id(news_id: int, file: UploadFile | None = None,
                           patch_data: NewsPatchScheme | None = Body(default=None),
                           session: AsyncSession = Depends(get_async_session),
                           current_user: User = Depends(current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

    news: News | None = await session.get(News, news_id, options=(
        selectinload(News.comments),
        selectinload(News.author),
        selectinload(News.file),
        selectinload(News.comments, Comment.author),
    ))

    if news is None:
        raise HTTPException(404, detail=f'no news with id {news_id}')

    if patch_data is not None:
        data = patch_data.dict()
        for key in data:
            setattr(news, key, data[key])

        session.add(news)
        await session.commit()
        await session.refresh(news)

    if file is not None:
        file_path = await save_file(file)

        request = select(NewsFile).where(NewsFile.news_id == news.id)
        news_file: NewsFile | None = (await session.execute(request)).scalars().first()

        if news_file is not None:
            os.remove(news_file.file_path)
            news_file.file_path = file_path
        else:
            news_file = NewsFile(news_id=news.id, file_path=file_path,
                                 file_format=get_settings().IMAGE_CONTROLLER.file_format)

        session.add(news_file)
        await session.commit()
        await session.refresh(news_file)

    return NewsRead.from_orm(news)


@router.delete('/{news_id}', status_code=204)
async def delete_news(news_id: int, session: AsyncSession = Depends(get_async_session),
                      current_user: User = Depends(current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail=f'user {current_user.id} is not a superuser')

    news: News | None = await session.get(News, news_id, options=(
        selectinload(News.comments),
        selectinload(News.author),
        selectinload(News.file),
        selectinload(News.comments, Comment.author),
    ))

    if news is None:
        raise HTTPException(404, detail=f'no news with id {news_id}')

    if news.file and os.path.exists(news.file.file_path):
        os.remove(news.file.file_path)
        await session.delete(news.file)

    for comment in news.comments:
        await session.delete(comment)

    request = select(NewsRating).where(NewsRating.news_id == news.id)
    for rating in (await session.execute(request)).scalars().all():
        await session.delete(rating)

    await session.delete(news)
