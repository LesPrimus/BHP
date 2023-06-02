import ipaddress
import sys
from ctypes import Structure, c_ubyte, c_ushort, c_uint32
import socket
import threading
import time

SUBNET = "192.168.1.0/24"
MESSAGE = "PYTHONROCK!"


class IP(Structure):
    _fields_ = [
        ("version", c_ubyte, 4),
        ("ihl", c_ubyte, 4),
        ("tos", c_ubyte, 8),
        ("len", c_ushort, 16),
        ("id", c_ushort, 16),
        ("offset", c_ushort, 16),
        ("ttl", c_ubyte, 8),
        ("protocol_num", c_ubyte, 8),
        ("sum", c_ushort, 16),
        ("src", c_uint32, 32),
        ("dst", c_uint32, 32),
    ]

    def __new__(cls, socket_buffer=None):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):
        super().__init__(socket_buffer=socket_buffer)

    def __str__(self):
        return f"{self.__class__.__name__}" \
               f"(src_address={self.src_address}, " \
               f"dst_address={self.dst_address}), " \
               f"protocol={self.protocol})"

    @property
    def src_address(self):
        return ipaddress.ip_address(self.src)

    @property
    def dst_address(self):
        return ipaddress.ip_address(self.dst)

    @property
    def protocol(self):
        try:
            return {1: "ICMP", 6: "TCP", 17: "UDP"}[self.protocol_num]
        except KeyError:
            print(f"No protocol for {self.protocol_num}")
            return str(self.protocol_num)


class ICMP(Structure):
    _fields_ = [
        ("type", c_ubyte, 8),
        ("code", c_ubyte, 8),
        ("header_chk_sum", c_ushort, 16),
        ("unused", c_ushort, 16),
        ("next_hop_mtu", c_ushort, 16),
    ]

    def __new__(cls, socket_buffer=None):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):
        super().__init__(socket_buffer=socket_buffer)

    def __str__(self):
        return f"{self.__class__.__name__}" \
               f"(type={self.type}, code={self.code})"


def udp_sender():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for ip in ipaddress.ip_network(SUBNET).hosts():
            sender.sendto(MESSAGE.encode(), (str(ip), 65212))


class Scanner:
    def __init__(self, host):
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.socket.bind((host, 0))

    def sniff(self):
        hosts_up = set()
        try:
            while True:
                raw_buffer = self.socket.recvfrom(65535)[0]
                ip_header = IP(raw_buffer[0:20])
                if ip_header.protocol == "ICMP":
                    offset = ip_header.ihl * 4
                    buf = raw_buffer[offset: offset + 8]
                    icmp_header = ICMP(buf)
                    if icmp_header.code == 3 and icmp_header.type == 3:
                        if ipaddress.ip_address(ip_header.src_address) in ipaddress.IPv4Network(SUBNET):
                            if raw_buffer[len(raw_buffer) - len(MESSAGE):] == bytes(MESSAGE, 'utf8'):
                                tgt = str(ip_header.src_address)
                                if tgt != self.host and tgt not in hosts_up:
                                    hosts_up.add(str(ip_header.src_address))
                                    print(f"Host-Up: {tgt}")
        except KeyboardInterrupt:
            sys.exit()


if __name__ == '__main__':
    host = "192.168.1.48"
    s = Scanner(host)
    time.sleep(5)
    t = threading.Thread(target=udp_sender)
    t.start()
    s.sniff()
