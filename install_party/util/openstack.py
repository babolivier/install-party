import ipaddress

from novaclient import client as novaclient

# Only imported for type hints.
from novaclient.v2.client import Client as V2Client


def get_nova_client(config) -> V2Client:
    openstack_config = config["openstack"]
    nova_client = novaclient.Client(
        version=openstack_config["api_version"],
        auth_url=openstack_config["auth_url"],
        username=openstack_config["username"],
        password=openstack_config["password"],
        project_id=openstack_config["tenant_id"],
        project_name=openstack_config["tenant_name"],
        region_name=openstack_config["region_name"],
    )

    return nova_client


def get_ipv4(instance):
    # Get the instance's IPv4 address from its metadata.
    # We need to loop through all of the interfaces of the Ext-Net
    # network (which is the public-facing network) because we can't
    # always know how the interfaces are ordered.
    interfaces = instance.addresses.get("Ext-Net")
    if interfaces is None:
        return None

    ip_address = None
    for interface in interfaces:
        address = interface["addr"]
        try:
            # This will raise an AddressValueError exception if the
            # value isn't an IPv4 address.
            ipaddress.IPv4Address(address)
            # If no exception have been raised, then the address is an
            # IPv4 address.
            ip_address = address
        except ipaddress.AddressValueError:
            # This address isn't an IPv4 address; continue to the
            # next interface.
            continue

    return ip_address
