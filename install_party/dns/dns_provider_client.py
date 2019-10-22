import abc
from typing import List


class DNSRecord:
    def __init__(self, record_id: str, sub_domain: str, target: str, zone: str):
        self.record_id = record_id
        self.sub_domain = sub_domain
        self.target = target
        self.zone = zone


class DNSProviderClient(abc.ABC):
    @abc.abstractmethod
    def create_sub_domain(self, record_name: str, target: str, zone: str) -> DNSRecord:
        pass

    @abc.abstractmethod
    def get_sub_domains(self, namespace: str, zone: str) -> List[DNSRecord]:
        pass

    @abc.abstractmethod
    def delete_sub_domain(self, record: DNSRecord):
        pass

    @abc.abstractmethod
    def commit(self, zone: str):
        pass
