import datetime
import os
from multiprocessing import Queue

from dotenv import load_dotenv
from requests import get

from config import get_settings
from processes.processes_manager import ProcessesManagerError


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
    raise ProcessesManagerError(json)


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
    raise ProcessesManagerError(json)


def get_long_poll_changes(data: dict, time: int) -> dict:
    response = get(f'{data["server"]}?act=a_check&key={data["key"]}&ts={data["ts"]}&wait={time}')
    json = response.json()

    if response.status_code == 200 and 'ts' in json and 'updates' in json:
        data['ts'] = json['ts']
        return json['updates']
    raise ProcessesManagerError(json)


def vk_process(connection: Queue):
    def update_output_data(base, new_data):
        base['count'] += (1 if base['count'] != 100 else 0)
        base['items'] = [new_data] + (base['items'] if base['count'] != 100 else base['items'][:-1])
        return base

    print('vk_process started')

    wait_time = os.getenv('VK_WAIT')
    settings = get_settings()
    data_dict = get_long_poll_data()

    output_data = get_load_vk_data()
    connection.put(output_data)

    while True:
        try:
            if settings.DEBUG:
                data = print_time_log('vk_process', get_long_poll_changes, data_dict, wait_time)
            else:
                data = get_long_poll_changes(data_dict, wait_time)

            if data:
                output_data = update_output_data(output_data, data[0]['object'])
                connection.put(output_data)
        except Exception as error:
            print(f'vk_process function error: {error}')
