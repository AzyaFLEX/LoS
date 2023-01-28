from functools import lru_cache
from multiprocessing import Queue

import _queue


class ProcessesManagerError(Exception): ...


class ProcessesManager:
    VK_PROCESS_QUEUE: Queue = None
    VK_DATA: dict = None

    def update_vk_data(self):
        if self.VK_PROCESS_QUEUE is None:
            raise ProcessesManagerError('miss VK_PROCESS_QUEUE')

        try:
            data = self.VK_PROCESS_QUEUE.get(timeout=float('-inf'))
            self.VK_DATA = data
        except _queue.Empty:
            return


@lru_cache
def get_processes_manager() -> ProcessesManager:
    return ProcessesManager()
