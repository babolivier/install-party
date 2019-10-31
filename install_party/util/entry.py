from install_party.dns.dns_provider_client import DNSRecord
from install_party.instances.instances_provider_client import Instance


class Entry:
    def __init__(self, instance: Instance = None, record: DNSRecord = None):
        self.instance = instance
        self.record = record
