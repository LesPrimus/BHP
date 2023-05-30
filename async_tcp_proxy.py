import asyncio
import argparse
import sys
import textwrap

HEX_FILTER = ''.join(
    [(len(repr(chr(i))) == 3) and chr(i) or '.' for i in range(256)]
)


class TcpProxy:
    def __init__(
            self,
            local_host: str,
            local_port: int,
            remote_host: str,
            remote_port: int,
            receive_first: bool,
    ):
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.receive_first = receive_first

        self.remote_reader = None
        self.remote_writer = None

    async def handle(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
    ):
        if self.receive_first:
            remote_data = await self.remote_reader.read(4096)
            print('[<==] Remote send.')
            self.hexdump(remote_data)
            writer.write(remote_data)
            await writer.drain()
            self.receive_first = False
        while True:
            local_buffer = await reader.read(4096)
            if local_buffer:
                print("[==>]Local send.")
                self.hexdump(local_buffer)
                self.remote_writer.write(local_buffer)
                await self.remote_writer.drain()

            remote_buffer = await self.remote_reader.read(4096)
            if remote_buffer:
                print("[<==] Remote send.")
                self.hexdump(remote_buffer)
                writer.write(remote_buffer)
                await writer.drain()

            if not local_buffer or not remote_buffer:
                writer.close()
                await writer.wait_closed()
                break

    async def init_remote_connection(self):
        try:
            self.remote_reader, self.remote_writer = await asyncio.open_connection(self.remote_host, self.remote_port)
        except Exception as exc:
            print(f"Unable to open a connection to {self.remote_host} {str(exc)}")
            sys.exit(0)

    async def run(self):
        await self.init_remote_connection()
        server = await asyncio.start_server(self.handle, self.local_host, self.local_port)
        addrs = " ".join(str(sock.getsockname()) for sock in server.sockets)
        print(f'Serving on {addrs}')

        async with server:
            await server.serve_forever()
        self.remote_writer.close()
        await self.remote_writer.wait_closed()

    @staticmethod
    def hexdump(src, length=16, show=True):
        if isinstance(src, bytes):
            src = src.decode()
        results = list()
        for idx, chunk in enumerate([src[i: i + length] for i in range(0, len(src), length)]):
            printable = chunk.translate(HEX_FILTER)
            hexa = " ".join(f'{ord(c):02X}' for c in chunk)
            hex_width = length * 3
            results.append(
                f'{idx:04X} {hexa:<{hex_width}} {printable}'
            )
        if show:
            for line in results:
                print(line)
        else:
            return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="BHP TCP Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Example:
        async_tcp_proxy.py -lh 192.168.1.48 -lp 9000 -rh 10.12.132.1 -rp 9000 -rf
        async_tcp_proxy.py -lh 192.168.1.48 -lp 9000 -rh 10.12.132.1 -rp 9000 
        ''')
    )
    parser.add_argument('-lh', '--local-host', required=True)
    parser.add_argument('-lp', '--local-port', required=True, type=int)
    parser.add_argument('-rh', '--remote-host', required=True)
    parser.add_argument('-rp', '--remote-port', required=True, type=int)
    parser.add_argument('-rf', '--receive-first', action="store_true")

    args = parser.parse_args()

    proxy = TcpProxy(
        args.local_host,
        args.local_port,
        args.remote_host,
        args.remote_port,
        args.receive_first
    )
    asyncio.run(proxy.run())
