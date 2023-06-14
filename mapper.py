import asyncio
import pathlib
from http import HTTPStatus

import httpx

EXCLUDE = {'.jpg', '.gif', '.png', '.css'}
NR_WORKERS = 5


def gather_paths(path: str,  q: asyncio.Queue):
    root = pathlib.Path(path)
    for path in root.rglob("*"):
        if path.is_file() and path.suffix not in EXCLUDE:
            q.put_nowait(
                str(pathlib.Path("/").joinpath(path.relative_to(root)))
            )


async def worker(worker_name, job_queue: asyncio.Queue, results_queue: asyncio.Queue, client: httpx.AsyncClient):
    while not job_queue.empty():
        path = await job_queue.get()
        try:
            res = await client.get(path)
        except httpx.TimeoutException:
            pass
        else:
            if res.status_code == HTTPStatus.OK:
                print(f"[{worker_name}] -- <{res.url}> --> {res.status_code}")
                await results_queue.put(res)
        job_queue.task_done()


async def main(dir_path: str, target_url: str):

    job_queue = asyncio.Queue()
    result_queue = asyncio.Queue()

    # Gather path from dir
    gather_paths(dir_path, job_queue)

    async with httpx.AsyncClient(
        base_url=target_url,
    ) as client:
        for n in range(NR_WORKERS):
            worker_name = f"Worker-{n}"
            asyncio.create_task(worker(worker_name, job_queue, result_queue, client))

        await job_queue.join()

    with open("server_answers.txt", "w") as f:
        while not result_queue.empty():
            ok_response: httpx.Response = await result_queue.get()
            f.write(f'{ok_response.url}\n')

if __name__ == '__main__':
    root_dir = "/home/path/to/wordpress"
    target_url = "http://0.0.0.0:8000/"
    asyncio.run(main(root_dir, target_url))
