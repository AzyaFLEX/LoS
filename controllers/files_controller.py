import os
from idlelib.configdialog import is_int
from string import ascii_letters


class FileController:
    def __init__(self, directory: str, file_const: str = ascii_letters, file_format='jpg'):
        self.create_dir(directory, pre=True)

        self.file_const = file_const

        if len(file_const) % 2:
            raise Exception('file_const not a multiple of 2')

        self.directory = directory
        self.file_format = file_format

        self.current_path = self.get_last_path()

        self.current_file_index = self.get_last_file_index()

    def get_last_path(self) -> str:
        current_dir = self.file_const[:2]

        if not os.path.isdir(f'{self.directory}/{current_dir}'):
            os.mkdir(f'{self.directory}/{current_dir}')

        while os.path.isdir(path := f'{self.directory}/{current_dir}')\
                and f'999.{self.file_format}' in os.listdir(path):
            current_dir = self.next_dir()

        return current_dir

    def get_last_file_index(self) -> int:
        def check_format(filename: str):
            data = filename.split('.')

            if len(data) != 2:
                return False

            if data[-1] != self.file_format:
                return False

            if not is_int(data[0]):
                return False

            return True

        path = f'{self.directory}/{self.current_path}'
        files = [item for item in os.listdir(path) if os.path.isfile(f'{path}/{item}')]
        files = sorted(filter(check_format, files), key=lambda filename: int(filename.split('.')[0]))
        return int(files[-1].split('.')[0]) if files else 0

    def create_dir(self, path: str, pre=False):
        if not pre:
            path = f'{self.directory}/{path}'

        if not os.path.isdir(path):
            os.mkdir(path)

    def next_dir(self) -> str:
        def check_prev_dir(data):
            for depth in range(-2, -len(data) - 1, -1):
                if data[depth] != self.file_const[-2:]:
                    next_value = self.file_const.find(data[depth]) + 2
                    return data[:depth] + [self.file_const[next_value: next_value + 2]] \
                           + [self.file_const[:2]] * (-depth - 1)
            return [self.file_const[:2] for _ in range(len(data) + 1)]

        directories = self.current_path.split('/')
        current_value = self.file_const.find(directories[-1])
        if current_value == -1:
            raise FileNotFoundError(f'current dir can\'t be "{self.current_path}"')

        if current_value != len(self.file_const) - 2:
            directories[-1] = self.file_const[current_value + 2:current_value + 4]
        else:
            directories = check_prev_dir(directories)

        return '/'.join(directories)

    def get_filename(self) -> str:
        self.current_file_index = (self.current_file_index + 1) % 1000

        if not self.current_file_index:
            self.current_file_index += 1
            self.create_dir(self.next_dir())
        
        return f'{self.directory}/{self.current_path}/{str(self.current_file_index).rjust(3, "0")}.{self.file_format}'
