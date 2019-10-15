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
