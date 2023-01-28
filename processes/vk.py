import datetime
import os
from multiprocessing import Queue

from blingfire import text_to_sentences
from dotenv import load_dotenv
from requests import get

from config import get_settings
from routers.schemas import VkNewsRead


class VkProcessError(Exception): ...


def print_time_log(process_name, function, *args, **kwargs):
    started_time = datetime.datetime.now()
    output_data = function(*args, **kwargs)
    print(f'{process_name} iteration duration: {datetime.datetime.now() - started_time}')
    return output_data


def get_load_vk_data() -> dict:
    params = {
        'access_token': os.getenv('VK_SERVER_KEY'),
        'owner_id': f'-{os.getenv("VK_GROUP_ID")}',
        'v': 5.131
    }

    data = get('https://api.vk.com/method/wall.get', params=params)
    json = data.json()

    if data.status_code == 200 and 'response' in json:
        return json['response']
    raise VkProcessError(f'get_load_vk_data: {json}')


def get_long_poll_data() -> dict:
    load_dotenv()

    params = {
        'access_token': os.getenv('VK_GROUP_KEY'),
        'group_id': os.getenv('VK_GROUP_ID'),
        'v': 5.131
    }

    data = get('https://api.vk.com/method/groups.getLongPollServer', params=params)
    json = data.json()

    if data.status_code == 200 and 'response' in json:
        return json['response']
    raise VkProcessError(f'get_long_poll_data: {json}')


def get_long_poll_changes(data: dict, time: int) -> dict | str | None:
    response = get(f'{data["server"]}?act=a_check&key={data["key"]}&ts={data["ts"]}&wait={time}')
    json = response.json()

    if response.status_code == 200 and 'ts' in json and 'updates' in json:
        data['ts'] = json['ts']
        if json['updates']:
            return process_data_dict(json['updates'][0]['object'])
        return
    elif 'failed' in json and json['failed'] == 2:
        return 'update_long_poll_data'
    raise VkProcessError(f'get_long_poll_changes: {json}')


def process_data_dict(data: dict) -> VkNewsRead | None:
    if 'text' not in data:
        return

    sentences = text_to_sentences(data['text']).split('\n')

    class FromOrmData:
        def __init__(self):
            self.title = sentences[0] if sentences[0] else None
            self.content = (' '.join(sentences[1:6]) + ('...' if len(sentences) > 6 else '')) if data['text'] else None
            self.image_url = None
            self.link = f'https://vk.com/wall-{os.getenv("VK_GROUP_ID")}_{data["id"]}'

    object_data = FromOrmData()

    for content in data['attachments']:
        if content['type'] not in {'photo', 'video', 'link'}:
            continue

        content = content[content['type']]
        if 'image' in content:
            object_data.image_url = content['first_frame'][-1]['url']
        elif 'photo' in content:
            object_data.image_url = content['photo']['sizes'][-1]['url']
        elif 'sizes' in content:
            object_data.image_url = content['sizes'][-1]['url']

    for attr in object_data.__dict__:
        if getattr(object_data, attr) is None:
            delattr(object_data, attr)

    return VkNewsRead.from_orm(object_data)


def vk_process(connection: Queue):
    print('vk_process started')

    wait_time = os.getenv('VK_WAIT')
    settings = get_settings()
    data_dict = get_long_poll_data()

    output_data = []
    for dictionary in get_load_vk_data()['items']:
        output_data += [process_data_dict(dictionary)]

    connection.put(output_data)

    while True:
        try:
            if settings.DEBUG:
                data = print_time_log('vk_process', get_long_poll_changes, data_dict, wait_time)
            else:
                data = get_long_poll_changes(data_dict, wait_time)

            if data == 'update_long_poll_data':
                data_dict = get_long_poll_data()
            elif data:
                if len(output_data) == 100:
                    output_data = [data] + output_data[:-1]
                else:
                    output_data = [data] + output_data

                connection.put(output_data)
        except Exception as error:
            print(f'vk_process function error: {error}')
