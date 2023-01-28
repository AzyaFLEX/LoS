from functools import lru_cache
from multiprocessing import Queue


class ProcessesManagerError(Exception): ...


class ProcessesManager:
    VK_GET_QUEUE: Queue = Queue()
    VK_SEND_QUEUE: Queue = Queue()
    VK_DATA: dict = None

    def update_vk_data(self):
        if not self.VK_GET_QUEUE.empty():
            self.VK_DATA = self.VK_GET_QUEUE.get(timeout=float('-inf'))

    def forced_update_vk_data(self):
        self.VK_SEND_QUEUE.put('force_update')


@lru_cache
def get_processes_manager() -> ProcessesManager:
    return ProcessesManager()
