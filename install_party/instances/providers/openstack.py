import ipaddress
import logging
from typing import List

from novaclient import client as nova_client

# Only imported for type hints.
from novaclient.v2.client import Client as V2Client

from install_party.instances.instances_provider_client import (
    Instance,
    InstancesProviderClient,
)
from install_party.util.errors import InstanceCreationError

logger = logging.getLogger(__name__)


class OpenStackInstancesProviderClient(InstancesProviderClient):
    def __init__(self, args):
        self.client: V2Client = nova_client.Client(
            version=args["api_version"],
            auth_url=args["auth_url"],
            username=args["username"],
            password=args["password"],
            project_id=args["tenant_id"],
            project_name=args["tenant_name"],
            region_name=args["region_name"],
        )

        self.image_id = args["image_id"]
        self.flavor_id = args["flavor_id"]

    def create_instance(self, name: str, post_creation_script: str) -> Instance:
        server = self.client.servers.create(
            name=name,
            image=self.image_id,
            flavor=self.flavor_id,
            userdata=post_creation_script,
        )

        logger.info("Waiting for instance to become active...")

        # Wait for the instance to become active.
        status = ""
        while status != "ACTIVE":
            server = self.client.servers.list(search_opts={
                "name": name,
            })[0]

            status = server.status

            if status == "ERROR":
                raise InstanceCreationError(
                    "The instance status changed to ERROR.")

        return Instance(server.id, name, get_ipv4(server), status)

    def get_instances(self, namespace: str) -> List[Instance]:
        # Retrieve all instances which name starts with the namespace and is followed by
        # "-".
        servers = self.client.servers.list(search_opts={
            "name": "%s-*" % namespace
        })

        instances = []

        for server in servers:
            instances.append(Instance(
                server.id, server.name, get_ipv4(server), server.status
            ))

        return instances

    def delete_instance(self, instance: Instance):
        self.client.servers.delete(instance.instance_id)

    def commit(self):
        pass


provider_client_class = OpenStackInstancesProviderClient


def get_ipv4(server):
    """Get the server's public IPv4 address from its metadata.

    Loops through all of the interfaces of the Ext-Net network (which is the public-facing
    network) because we can't always know how the interfaces are ordered.

    Args:
         server (Server): The server to retrieve the IPv4 of, as an instance of the Server
            class from the nova SDK.
    """

    interfaces = server.addresses.get("Ext-Net")
    if interfaces is None:
        return None

    ip_address = None
    for interface in interfaces:
        address = interface["addr"]
        try:
            # This will raise an AddressValueError exception if the value isn't an IPv4
            # address.
            ipaddress.IPv4Address(address)
            # If no exception have been raised, then the address is an IPv4 address.
            ip_address = address
        except ipaddress.AddressValueError:
            # This address isn't an IPv4 address; continue to the next interface.
            continue

    return ip_address
