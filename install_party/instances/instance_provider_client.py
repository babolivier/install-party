import abc
from typing import List


class Instance:
    def __init__(self, id: str, name: str, ip_address: str, status: str):
        self.id = id
        self.name = name
        self.ip_address = ip_address
        self.status = status


class InstanceProviderClient(abc.ABC):
    @abc.abstractmethod
    def create_instance(self, name: str, post_creation_script: str) -> Instance:
        pass

    @abc.abstractmethod
    def get_instances(self, namespace: str) -> List[Instance]:
        pass

    @abc.abstractmethod
    def delete_instance(self, instance: Instance):
        pass

    @abc.abstractmethod
    def commit(self):
        pass
