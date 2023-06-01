import asyncio

import asyncssh
import sys
import logging

logging.basicConfig(level="DEBUG")
asyncssh.set_debug_level(2)


async def run_client() -> None:
    async with asyncssh.connect(
            '192.168.1.57',  # server-host
            8022,  # server-port
            username="foo",
            password="bar",
            known_hosts=None
    ) as conn:
        listener = await conn.forward_remote_port(
            "",  # Server reverse forward host
            8080,  # Server reverse forward port
            "httpbin.org",  # Client reverse forward host
            80  # Client reverse forward port
        )

        await listener.wait_closed()

loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(run_client())
except (OSError, asyncssh.Error) as exc:
    sys.exit('SSH connection failed: ' + str(exc))
