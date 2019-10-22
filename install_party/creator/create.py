import argparse
import logging
import random
import string
import sys
import time
import os

import requests

from install_party.dns import dns_provider
from install_party.util import errors, openstack

logger = logging.getLogger(__name__)


def random_string(n):
    """Generate a random string made of n lowercase letters."""
    return ''.join(random.choices(string.ascii_lowercase, k=n))


def create_instance(name, expected_domain, config):
    """Create the instance with a boot script using the OpenStack Nova API, then wait for
    the instance to become active (and raise an exception if an error occurred).

    Args:
        name (str): The suffix for the name of the instance to create. The final name will
            be "namespace-name" where "namespace" is the namespace defined in the
            configuration.
        expected_domain (str): The domain name that is expected to be attached to the
            instance later in the creation process.
        config (dict): The parsed configuration.

    Returns:
        str: the IPv4 address of the instance.

    Raises:
        InstanceCreationError: When waiting for the instance's status to become ACTIVE, it
            instead became ERROR.
    """
    nova_client = openstack.get_nova_client(config)

    logger.info("Creating instance...")

    # Generate the actual script to run post-creation from the template and the
    # configuration.
    post_creation_script_path = os.path.join(sys.prefix, "scripts/post_create.sh")
    post_creation_script = open(post_creation_script_path).read().format(
        user=config["instances"]["user"],
        password=config["instances"]["password"],
        riot_version=config["general"]["riot_version"],
        expected_domain=expected_domain,
    )

    # Ask the hypervisor to create a new instance.
    openstack_config = config["openstack"]
    instance = nova_client.servers.create(
        name="%s-%s" % (config["general"]["namespace"], name),
        image=openstack_config["image_id"],
        flavor=openstack_config["flavor_id"],
        userdata=post_creation_script,
    )

    logger.info("Waiting for instance to become active...")

    # Wait for the instance to become active.
    status = ""
    while status != "ACTIVE":
        instance = nova_client.servers.list(search_opts={
            "name": name,
        })[0]

        status = instance.status

        if status == "ERROR":
            raise errors.InstanceCreationError("The instance status changed to ERROR.")

    return openstack.get_ipv4(instance)


def create_record(name, ip_address, config):
    """Create a DNS A record to attach to an instance using the DNS provider's API.

    Args:
        name (str): The prefix for the DNS record's subdomain. The final subdomain will be
            "name.namespace" where "namespace" is the namespace defined in the
            configuration.
        ip_address (str): The IPv4 address to attach the DNS A record to.
        config (dict): The parsed configuration.

    Returns:
         The created DNS record.
    """
    client = dns_provider.get_dns_provider_client(config)

    logger.info("Creating DNS record...")

    zone = config["dns"]["zone"]
    sub_domain = "%s.%s" % (name, config["general"]["namespace"])

    record = client.create_sub_domain(sub_domain, ip_address, zone)

    # Apply the new configuration.
    client.commit(zone)

    return record


def create(config):
    """Create an instance, attach a domain name to it, and wait until the instance's
    boot script has been run.

    Args:
        config (dict): The parsed configuration.
    """
    args = parse_args()

    # Generate a random name (5 lowercase letters) if none was provided.
    if args.name is None:
        name = random_string(5)
    else:
        name = args.name

    # Guess what the final domain name for the host is going to be. This is used for
    # inserting the right values in the post-creation script template.
    expected_domain = "%s.%s.%s" % (
        name, config["general"]["namespace"], config["dns"]["zone"]
    )

    logger.info(
        "Provisioning host %s (expected domain name %s)" % (name, expected_domain)
    )
    # Create the instance with the OpenStack API.
    ip_address = create_instance(name, expected_domain, config)
    logger.info("Host is active, IPv4 address is", ip_address)
    # Create a DNS A record for the instance's IP address using the DNS provider's API.
    record = create_record(name, ip_address, config)
    # We use the data the API gave us in response to highlight any possible mismatch
    # between the domain name we guessed and the one we actually created.
    logger.info("Created DNS record %s.%s" % (record.sub_domain, record.zone))

    logger.info("Waiting for post-creation script to finish...")
    # Every second, check if we can reach the host's HTTPS server, and only exit it if we
    # got a response. Because starting up the HTTP(S) server is the last operation
    # performed by the post-creation script, reaching this condition means that the
    # execution finished successfully.
    while True:
        time.sleep(1)

        try:
            requests.get("http://%s" % expected_domain)
            break
        except Exception:
            continue

    logger.info("Done!")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party create",
        description="Create a new instance and attach a domain name to it.",
    )
    parser.add_argument(
        "--name",
        help="Name to give the instance, and to build its domain name from. Defaults to a"
             " random string of 5 lowercase letters. Can only contain the characters"
             " allowed in a domain name label."
    )

    return parser.parse_args()
