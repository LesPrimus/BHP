import asyncio
from http import HTTPStatus

import httpx

AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:19.0) Gecko/20100101 Firefox/19.0"
EXTENSIONS = ['.php', '.bak', '.orig', '.inc', '.py']
TARGET = "http://testphp.vulnweb.com"
WORKER_NR = 5
WORDLIST = "/path/to/wordslist.txt"


def populate_job_queue(job_queue: asyncio.Queue):
    with open(WORDLIST) as f:
        for line in f.readlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            job_queue.put_nowait(line)
            for ext in EXTENSIONS:
                job_queue.put_nowait(f'{line}{ext}')


async def bruter(name, job_queue: asyncio.Queue, result_queue: asyncio.Queue, client: httpx.AsyncClient):
    while not job_queue.empty():
        url_path = await job_queue.get()
        try:
            res = await client.get(url_path)
        except httpx.TimeoutException:
            pass
        else:
            print(f"[{name}] -- {res.url} -- {res.status_code}")
            if res.status_code == HTTPStatus.OK:
                await result_queue.put(res)
        finally:
            job_queue.task_done()


async def main():
    job_queue = asyncio.Queue()
    result_queue = asyncio.Queue()
    populate_job_queue(job_queue)

    async with httpx.AsyncClient(
            headers={"User-Agent": AGENT},
            base_url=TARGET,
            timeout=1
    ) as client:
        for n in range(WORKER_NR):
            worker_name = f"Worker-{n}"
            asyncio.create_task(bruter(worker_name, job_queue, result_queue, client))

        await job_queue.join()

asyncio.run(main())
