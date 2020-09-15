import datetime
import os
import pathlib
import shutil
from functools import wraps
from uuid import uuid4


def get_path(root_path, *sub_folders, file=None):
    final_path = os.path.join(root_path, *sub_folders)
    pathlib.Path(final_path).mkdir(parents=True, exist_ok=True)
    if file:
        return os.path.join(final_path, file)
    else:
        return final_path


class open_temp_directory:
    def __init__(self, root_path, generator_type='uuid4'):
        self.path = ''
        self.root_path = root_path
        if generator_type == 'uuid4':
            self.generator = uuid4
        elif generator_type == 'timestamp':
            self.generator = lambda: str(int(datetime.datetime.now().timestamp()))
        elif generator_type == 'seconds':
            now = datetime.datetime.now()
            self.generator = lambda: '{:0>5}'.format(now.hour * 3600 + now.minute * 60 + now.second)
        else:
            raise Exception('INVALID GENERATOR TYPE')

    def __enter__(self):
        while True:
            try:
                root_path = self.root_path() if callable(self.root_path) else self.root_path
                self.path = os.path.join(root_path, str(self.generator()))
                pathlib.Path(self.path).mkdir(parents=True, exist_ok=False)
                return self.path
            except Exception as e:
                if 'already exists' in str(e):
                    self.path = ''
                    continue
                else:
                    raise

    def __exit__(self, *exc):
        if self.path:
            shutil.rmtree(self.path)

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self as temp_directory:
                kwargs['temp_directory'] = temp_directory
                return func(*args, **kwargs)

        return inner
