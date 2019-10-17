import ipaddress
import random
import string
import sys
import time
import os

import requests

from install_party.util import openstack, ovh


def random_string(n):
    return ''.join(random.choices(string.ascii_lowercase, k=n))


def create_instance(name, expected_domain, config):
    nova_client = openstack.get_nova_client(config)

    print("Creating instance...")

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

    print("Waiting for instance to become active...")

    # Wait for the instance to become active.
    status = ""
    while status != "ACTIVE":
        instance = nova_client.servers.list(search_opts={
            "name": name,
        })[0]

        status = instance.status

        if status == "ERROR":
            sys.stderr.write("An error occurred while building the instance. Aborting.\n")
            sys.exit(2)

    return openstack.get_ipv4(instance)


def create_record(name, ip_address, config):
    ovh_client = ovh.get_ovh_client(config)

    print("Creating DNS record...")

    # Create a new DNS record in the configured zone.
    record = ovh_client.post(
        "/domain/zone/%s/record" % config["general"]["dns_zone"],
        fieldType="A",
        subDomain="%s.%s" % (name, config["general"]["namespace"]),
        target=ip_address,
    )

    print("Refreshing the DNS zone...")

    # Refresh the DNS server's configuration to make it aware of the new record.
    ovh_client.post("/domain/zone/%s/refresh" % config["general"]["dns_zone"])

    return record


def create(name=None, config={}):
    # Generate a random name (5 lowercase letters) if none was provided.
    if name is None:
        name = random_string(5)

    # Guess what the final domain name for the host is going to be. This is used for
    # inserting the right values in the post-creation script template.
    expected_domain = "%s.%s.%s" % (
        name, config["general"]["namespace"], config["general"]["dns_zone"]
    )

    print("Provisioning host %s (expected domain name %s)" % (name, expected_domain))
    # Create the instance with the OpenStack API.
    ip_address = create_instance(name, expected_domain, config)
    print("Host is active, IPv4 address is", ip_address)
    # Create a DNS A record for the instance's IP address using OVH's API.
    record = create_record(name, ip_address, config)
    # We use the data the API gave us in response to highlight any possible mismatch
    # between the domain name we guessed and the one we actually created.
    print("Created DNS record %s.%s" % (record["subDomain"], record["zone"]))

    print("Waiting for post-creation script to finish...")
    # Every second, check if we can reach the host's HTTPS server, and only exit it if we
    # got a 200 OK response. Because starting up the HTTP(S) server is the last operation
    # performed by the post-creation script, reaching this condition means that the
    # execution finished successfully.
    while True:
        time.sleep(1)

        try:
            response = requests.get("https://%s" % expected_domain)
        except Exception:
            continue

        if response.status_code == 200:
            break

    print("Host created and provisioned!")
