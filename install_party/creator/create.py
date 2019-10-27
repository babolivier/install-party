import argparse
import datetime
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


def check_connectivity(domain_name, config):
    """Every second, check if we can reach the host's HTTPS server, and only exit it if we
    got a response.

    Because starting up the HTTP(S) server is the last operation performed by the
    post-creation script, reaching this condition means that the execution finished
    successfully.

    Args:
        domain_name (str): The domain name to perform the connectivity check on.
        config (dict): The parsed configuration.

    Raises:
        ConnectivityCheckError: The connectivity check had to be aborted (e.g. if it timed
            out)
    """

    before = datetime.datetime.now().timestamp()

    while True:
        time.sleep(1)

        try:
            requests.get("http://%s" % domain_name)
            break
        except Exception:
            now = datetime.datetime.now().timestamp()
            if now > before + config["general"]["connectivity_check_timeout"]:
                raise errors.ConnectivityCheckError("The connectivity check timed out.")

            continue


def create_server(name, config):
    """Create an instance, attach a domain name to it, and wait until the instance's
    boot script has been run.

    Args:
        name (str): The name of the server.
        config (dict): The parsed configuration.
    """

    # Guess what the final domain name for the host is going to be. This is used for
    # inserting the right values in the post-creation script template.
    expected_domain = "%s.%s.%s" % (
        name, config["general"]["namespace"], config["dns"]["zone"]
    )

    logger.info(
        "Provisioning server %s (expected domain name %s)" % (name, expected_domain)
    )
    # Create the instance with the OpenStack API.
    ip_address = create_instance(name, expected_domain, config)
    logger.info("Host is active, IPv4 address is %s", ip_address)
    # Create a DNS A record for the instance's IP address using the DNS provider's API.
    record = create_record(name, ip_address, config)
    # We use the data the API gave us in response to highlight any possible mismatch
    # between the domain name we guessed and the one we actually created.
    logger.info("Created DNS record %s.%s" % (record.sub_domain, record.zone))

    logger.info("Waiting for post-creation script to finish...")

    check_connectivity(expected_domain, config)

    logger.info("Done!")

    return expected_domain


def create(config):
    args = parse_args()

    if args.number:
        number_to_create = int(args.number)

        server_domain_names = []
        failures = 0

        # Create the n servers.
        for i in range(number_to_create):
            # Generate a random name for the server.
            name = random_string(5)
            try:
                # Create the server and stave its domain name.
                domain_name = create_server(name, config)
                server_domain_names.append(domain_name)
            except Exception as e:
                logger.error(
                    "An error happened while creating the server, skipping: %s", e
                )
                failures += 1

        if failures < number_to_create:
            if failures:
                logger.info(
                    "\n%d servers over %d have been created:",
                    number_to_create - failures, number_to_create
                )
            else:
                logger.info("\nAll servers have been created:")

            # Print the domain names of all of the servers created.
            for domain_name in server_domain_names:
                logger.info("\t- %s", domain_name)
        else:
            logger.info("\nAll servers have failed to create.")
    else:
        # Generate a random name (5 lowercase letters) if none was provided.
        if args.name is None:
            name = random_string(5)
        else:
            name = args.name

        # Create the server.
        try:
            create_server(name, config)
        except Exception as e:
            logger.error(
                "An error happened while creating the server, skipping: %s", e
            )


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party create",
        description="Create a new instance and attach a domain name to it.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-n", "--name",
        help="Name to give the instance, and to build its domain name from. Defaults to a"
             " random string of 5 lowercase letters. Can only contain the characters"
             " allowed in a domain name label. Cannot be used in combination with"
             " -N/--number."
    )
    group.add_argument(
        "-N", "--number",
        help="Number of servers to create. Each server's name will be a random string of"
             " 5 lowercase letters. Cannot be used in combination with -n/--name."
    )

    return parser.parse_args()
