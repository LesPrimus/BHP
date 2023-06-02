import ipaddress
import sys
from ctypes import Structure, c_ubyte, c_ushort, c_uint32
import socket
import threading
import time


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


def sniff(host):
    socket_protocol = socket.IPPROTO_ICMP
    sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)
    sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    sniffer.bind((host, 0))

    try:
        while True:
            raw_buffer = sniffer.recvfrom(65535)[0]
            ip_header = IP(socket_buffer=raw_buffer[0:20])
            print(ip_header)
            if ip_header.protocol == "ICMP":
                offset = ip_header.ihl * 4
                buf = raw_buffer[offset: offset + 8]
                res = ICMP(buf)
                print(res)

    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    sniff("192.168.1.48")
