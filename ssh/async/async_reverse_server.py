import asyncio
import asyncssh
import socket
import sys


async def run_commands(conn: asyncssh.SSHClientConnection) -> None:
    """Run a series of commands on the client which connected to us"""
    try:
        while True:
            cmd = input("Enter a command: ")
            if cmd == "exit":
                break
            result = await conn.run(cmd)
            print('Command:', result.command)
            print('Return code:', result.returncode)
            print('Stdout:')
            print(result.stdout, end='')
            print('Stderr:')
            print(result.stderr, end='')
            print(75 * '-')

    finally:
        conn.close()
        await conn.wait_closed()


async def start_reverse_server() -> None:
    """Accept inbound connections and then become an SSH client on them"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(False)

    sock.bind(("192.168.1.48", 2222))
    await asyncssh.listen_reverse(
        sock=sock,
        client_keys=['server_key'],
        known_hosts='trusted_client_host_keys',
        acceptor=run_commands
    )

loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(start_reverse_server())
except (OSError, asyncssh.Error) as exc:
    sys.exit('Error starting reverse server: ' + str(exc))

loop.run_forever()
