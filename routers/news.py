from fastapi import APIRouter, Depends, HTTPException

from controllers.user_controller import current_active_user
from db import User
from processes.processes_manager import get_processes_manager
from routers.schemas import VkNewsReadList

router = APIRouter(
    prefix="/news",
    tags=["news"],
)

process_manager = get_processes_manager()


@router.get('/from_vk', response_model=VkNewsReadList)
async def get_news_from_vk():
    process_manager.update_vk_data()
    data = process_manager.VK_DATA

    return VkNewsReadList(count=len(data), items=data)


@router.post('/from_vk/forced_reload', status_code=200)
async def forced_reload(current_user: User = Depends(current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, detail='Access denied')

    process_manager.forced_update_vk_data()
