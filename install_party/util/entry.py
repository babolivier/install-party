from novaclient.v2.servers import Server

from install_party.dns.dns_provider_client import DNSRecord


class Entry:
    def __init__(self, instance: Server = None, record: DNSRecord = None):
        self.instance = instance
        self.record = record
