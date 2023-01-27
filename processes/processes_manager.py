from functools import lru_cache
from multiprocessing import Queue
from blingfire import text_to_sentences
from typing import List

import _queue


class ProcessesManagerError(Exception): ...


class ProcessesManager:
    VK_PROCESS_QUEUE: Queue = None
    VK_DATA: dict = None

    def update_vk_data(self):
        from routers.schemas import VkNewsRead

        def vk_data_processing(process_data) -> List[VkNewsRead]:
            # TODO оптимизировать. Не пересчитывать одинаковые данные из процесса вк (дописать процесс вк)

            output = []

            for elm in process_data['items']:
                sentences = text_to_sentences(elm['text']).split('\n')
                image_url = None

                for content in elm['attachments']:
                    if content['type'] not in {'photo', 'video', 'link'}:
                        continue

                    content = content[content['type']]
                    if 'image' in content:
                        image_url = content['first_frame'][-1]['url']
                    elif 'photo' in content:
                        image_url = content['photo']['sizes'][-1]['url']
                    elif 'sizes' in content:
                        image_url = content['sizes'][-1]['url']

                output += [VkNewsRead(title=sentences[0], image_url=image_url,
                                      content=(' '.join(sentences[1:6]) + '...' if len(sentences) > 6 else ''))]

            return output

        if self.VK_PROCESS_QUEUE is None:
            raise ProcessesManagerError('miss VK_PROCESS_QUEUE')

        try:
            data = self.VK_PROCESS_QUEUE.get(timeout=float('-inf'))
            self.VK_DATA = vk_data_processing(data)
        except _queue.Empty:
            pass


@lru_cache
def get_processes_manager() -> ProcessesManager:
    return ProcessesManager()
