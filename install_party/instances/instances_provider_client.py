import abc
from typing import List


class Instance:
    def __init__(self, instance_id: str, name: str, ip_address: str, status: str):
        """The representation of an instance created or retrieved by the API client for
        the configured instances provider.

        Args:
            instance_id (str): The internal identifier of the instance.
            name (str): The name of the instance.
            ip_address (str): The IPv4 of the instance.
            status (str): The status of the instance (e.g. building, active, error, etc.).
        """
        self.instance_id = instance_id
        self.name = name
        self.ip_address = ip_address
        self.status = status


class InstancesProviderClient(abc.ABC):
    @abc.abstractmethod
    def create_instance(self, name: str, post_creation_script: str) -> Instance:
        """Create an instance using the instances provider's API.

        Args:
            name (str): The name of the instance to create.
            post_creation_script (str): The script to run once the instance has been
                created.

        Returns:
            The created instance as an Instance object.
        """
        pass

    @abc.abstractmethod
    def get_instances(self, namespace: str) -> List[Instance]:
        """Retrieve every instance that is part of the provided namespace, i.e. every
        instance which name starts with 'namespace-'.

        Args:
            namespace (str): The namespace to retrieve instances for.

        Returns:
            The instances as a list of Instance objects.
        """
        pass

    @abc.abstractmethod
    def delete_instance(self, instance: Instance):
        """Delete the provided instance.

        Args:
            instance (Instance): The instance to delete, as an Instance object.
        """
        pass

    @abc.abstractmethod
    def commit(self):
        """Apply the changes if necessary."""
        pass
