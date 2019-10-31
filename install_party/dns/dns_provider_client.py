import abc
import ipaddress
from typing import List


class DNSRecord:
    def __init__(self, record_id: str, sub_domain: str, target: str, zone: str):
        """The representation of a DNS record created or retrieved by the API client for
        the configured DNS provider.

        Args:
            record_id (str): The internal identifier of the record.
            sub_domain (str): The sub-domain for the record.
            target (str): The record's target. Must be a valid IPv4.
            zone (str): The DNS zone the record is in.
        """
        # This will raise an AddressValueError exception if the value isn't an IPv4
        # address.
        ipaddress.IPv4Address(target)

        self.record_id = record_id
        self.sub_domain = sub_domain
        self.target = target
        self.zone = zone


class DNSProviderClient(abc.ABC):
    @abc.abstractmethod
    def create_sub_domain(self, record_name: str, target: str, zone: str) -> DNSRecord:
        """Create a sub-domain using the DNS provider's API.

        Args:
            record_name (str): The name of the sub-domain, in the form 'name.namespace'.
            target (str): The target of the sub-domain. Must be a valid IPv4.
            zone (str): The DNS zone in which to create the sub-domain.

        Returns:
            The created DNS record as a DNSRecord object.
        """
        pass

    @abc.abstractmethod
    def get_sub_domains(self, namespace: str, zone: str) -> List[DNSRecord]:
        """Retrieve every sub-domain that is part of the provided namespace, i.e. every
        sub-domain that ends with '.namespace', in the provided DNS zone.

        Args:
            namespace (str): The namespace to retrieve sub-domains for.
            zone (str): The DNS zone to retrieve sub-domains in.

        Returns:
            The retrieved DNS records as a list of DNSRecord objects.
        """
        pass

    @abc.abstractmethod
    def delete_sub_domain(self, record: DNSRecord):
        """ Delete the provided sub-domain.

        Args:
            record (DNSRecord): The DNS record to delete.
        """
        pass

    @abc.abstractmethod
    def commit(self, zone: str):
        """Apply the changes on the DNS zone if necessary.

        Args:
            zone (str): The DNS zone to apply the changes for.
        """
        pass
