from fastapi import APIRouter

from processes.processes_manager import get_processes_manager
from routers.schemas import VkNewsReadList

router = APIRouter(
    prefix="/news",
    tags=["news"],
)


@router.get('/from_vk', response_model=VkNewsReadList)
async def get_news_from_vk():
    process_manager = get_processes_manager()
    process_manager.update_vk_data()
    data = process_manager.VK_DATA

    return VkNewsReadList(count=len(data), items=data)
