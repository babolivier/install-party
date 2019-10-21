import argparse

from tabulate import tabulate

from install_party.util import openstack, ovh


def gather_instances(entries_dict, config):
    """Gather all instances which name belongs to the namespace defined in the
    configuration and add their info to a given dict.

    Args:
        entries_dict (dict): The dict to add the instances' info to.
        config (dict): The parsed configuration.
    """
    nova_client = openstack.get_nova_client(config)

    print("Gathering instances...")

    # Retrieve all instances which name starts with the namespace and is followed by "-".
    instances = nova_client.servers.list(search_opts={
        "name": "%s-*" % config["general"]["namespace"]
    })

    # Edit the entries dictionary to add the instances' information.
    for instance in instances:
        entry_id = instance.name.split("-", 1)[1]
        if entry_id in entries_dict:
            entries_dict[entry_id]["instance"] = instance
        else:
            entries_dict[entry_id] = {"instance": instance}


def gather_domains(entries_dict, config):
    """Gather all domain names which subdomain belongs to the namespace defined in the
    configuration and add their info to a given dict.

    Args:
        entries_dict (dict): The dict to add the domain names' info to.
        config (dict): The parsed configuration.
    """
    ovh_client = ovh.get_ovh_client(config)

    print("Gathering domains...")

    # Retrieve all DNS records which sub domain ends with "." followed by the namespace.
    sub_domain_filter = "%25.{namespace}".format(
        namespace=config["general"]["namespace"],
    )

    record_ids = ovh_client.get(
        "/domain/zone/%s/record?subDomain=%s" % (
            config["general"]["dns_zone"], sub_domain_filter
        )
    )

    # Retrieve data on each sub domain.
    for record_id in record_ids:
        record = ovh_client.get(
            "/domain/zone/%s/record/%s" % (
                config["general"]["dns_zone"], record_id
            )
        )

        # Edit the entries dictionary to add the record's information.
        entry_id = record["subDomain"].split(".", 1)[0]
        if entry_id in entries_dict:
            entries_dict[entry_id]["domain"] = record
        else:
            entries_dict[entry_id] = {"domain": record}


def sort_entries(entries_dict):
    """Process a dict populated by gather_instances and gather_domains and sorts its
    entries into three lists: one containing the entries that have both an instance and a
    domain, one containing those that only have a domain, and one containing those that
    only have an instance.

    All lists are populated in such a way that they can be directly fed to the call to
    tabulate in get_and_print_list.

    Args:
        entries_dict (dict): The dict containing the entries to sort.

    Returns:
        list: The list containing the entries that have both an instance and a domain.
        list: The list containing the entries that only have a domain.
        list: The list containing the entries that only have an instance.
    """

    complete_entries = []
    orphaned_instances = []
    orphaned_domains = []
    for entries_dict, entry in entries_dict.items():
        instance = entry.get("instance")
        domain = entry.get("domain")

        if domain:
            # Generate the full domain name for this entry from the domain's info.
            full_domain = "%s.%s" % (domain["subDomain"], domain["zone"])

        if instance is None:
            # We're sure that domain is not None (and therefore full_domain is defined)
            # here because otherwise this ID wouldn't be in the dict.
            orphaned_domains.append([entries_dict, full_domain, domain["target"]])
        elif domain is None:
            # We're sure that instance is not None here because otherwise this ID wouldn't
            # be in the dict.
            orphaned_instances.append([
                entries_dict,
                instance.name,
                instance.status,
                openstack.get_ipv4(instance)
            ])
        else:
            complete_entries.append([
                entries_dict,
                instance.name,
                full_domain,
                instance.status,
                openstack.get_ipv4(instance)
            ])

    return complete_entries, orphaned_domains, orphaned_instances


def get_list(config):
    """Retrieve a list of all instances and domain names under a configured namespace.

    Args:
        config (dict): The parsed configuration.

    Returns:
        A dict containing the entries, looking like

        {
            "<id>": {"instance": ..., "domain": ...},
        }

        where "instance" is the instance associated with this ID (as returned by
        nova_client.servers.list) and "domain" is the domain name associated with this ID
        (a dict containing the response to
        https://api.ovh.com/console/#/domain/zone/%7BzoneName%7D/record/%7Bid%7D#GET)
    """
    # Initialise the empty dict which will be populated later.
    entries_dict = {}

    # Populate the dict with instances.
    gather_instances(entries_dict, config)
    # Populate the dict with domains.
    gather_domains(entries_dict, config)

    return entries_dict


def get_and_print_list(config):
    """Retrieve a list of all instances and domain names under a configured namespace and
    print a table listing them and associating each instance with its domain name.

    If an instance doesn't have a domain name associated, or vice-versa, the entry is
    listed in one of two extra tables (depending on what is missing). Each of those extra
    tables is only displayed if it contains at least one entry.

    Args:
        config (dict): The parsed configuration.
    """
    args = parse_args()

    # Retrieve the list of instances and domain names.
    entries_dict = get_list(config)

    # Sort the entries into three lists.
    complete_entries, orphaned_domains, orphaned_instances = sort_entries(entries_dict)

    # Print the lists.
    print(tabulate(
        complete_entries,
        headers=["Name", "Instance name", "Domain", "Status", "IPv4"],
        tablefmt="psql",
    ))

    if not args.hide_orphans:
        if orphaned_instances:
            print("\nORPHANED INSTANCES")
            print(tabulate(
                orphaned_instances,
                headers=["Name", "Instance name", "Status", "IPv4"],
                tablefmt="psql"
            ))

        if orphaned_domains:
            print("\nORPHANED DOMAINS")
            print(tabulate(
                orphaned_domains,
                headers=["Name", "Domain", "Status", "IPv4"],
                tablefmt="psql"
            ))


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party list",
        description="List existing servers.",
    )
    parser.add_argument(
        "--hide-orphans",
        action="store_true",
        help="Hide instances without a domain and domains without an instance. Defaults"
             " to false.",
    )

    return parser.parse_args()
