#!/usr/bin/env python

import os
import random
import string
import sys
import time

from novaclient import client as novaclient
import ovh
import requests
import yaml

# Only imported for type hints.
from novaclient.v2.client import Client as V2Client


def random_string(n):
    return ''.join(random.choices(string.ascii_lowercase, k=n))


def create_instance(name, expected_domain, config):
    openstack_config = config["openstack"]
    nova_client: V2Client = novaclient.Client(
        version=openstack_config["api_version"],
        auth_url=openstack_config["auth_url"],
        username=openstack_config["username"],
        password=openstack_config["password"],
        project_id=openstack_config["tenant_id"],
        project_name=openstack_config["tenant_name"],
        region_name=openstack_config["region_name"],
    )

    print("Creating instance...")

    # Generate the actual script to run post-creation from the template and the
    # configuration.
    post_creation_script = open("post_create.sh").read().format(
        user=config["instances"]["user"],
        password=config["instances"]["password"],
        riot_version=config["general"]["riot_version"],
        expected_domain=expected_domain,
    )

    # Ask the hypervisor to create a new instance.
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

    # Return the instance's IP address.
    return instance.addresses["Ext-Net"][0]["addr"]


def create_record(name, ip_address, config):
    ovh_config = config["ovh"]
    ovh_client = ovh.Client(
        endpoint=ovh_config["endpoint"],
        application_key=ovh_config["application_key"],
        application_secret=ovh_config["application_secret"],
        consumer_key=ovh_config["consumer_key"],
    )

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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: install_party.py [mode] [options]\n")
        sys.exit(1)

    config_location = os.getenv("INSTALL_PARTY_CONFIG", "config.yaml")
    config_content = open(config_location).read()
    config = yaml.safe_load(config_content)

    mode = sys.argv[1]

    if mode == "create":
        create(sys.argv[2] if len(sys.argv) > 2 else None, config)

