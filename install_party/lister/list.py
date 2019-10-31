import argparse
import logging
from typing import Dict

from tabulate import tabulate

from install_party.dns import dns_provider
from install_party.instances import instances_provider
from install_party.util.entry import Entry

logger = logging.getLogger(__name__)


def gather_instances(entries_dict: Dict[str, Entry], config):
    """Gather all instances which name belongs to the namespace defined in the
    configuration and add their info to a given dict.

    Args:
        entries_dict (dict): The dict to add the instances' info to.
        config (dict): The parsed configuration.
    """
    logger.debug("Gathering instances...")

    client = instances_provider.get_instances_provider_client(config)
    instances = client.get_instances(config["general"]["namespace"])

    # Edit the entries dictionary to add the instances' information.
    for instance in instances:
        entry_id = instance.name.split("-", 1)[1]
        if entry_id in entries_dict:
            entries_dict[entry_id].instance = instance
        else:
            entries_dict[entry_id] = Entry(instance=instance)


def gather_records(entries_dict: Dict[str, Entry], config):
    """Gather all DNS records which sub-domain belongs to the namespace defined in the
    configuration and add their info to a given dict.

    Args:
        entries_dict (dict): The dict to add the domain names' info to.
        config (dict): The parsed configuration.
    """
    client = dns_provider.get_dns_provider_client(config)

    logger.debug("Gathering DNS records...")

    records = client.get_sub_domains(
        config["general"]["namespace"], config["dns"]["zone"]
    )

    for record in records:
        # Edit the entries dictionary to add the record's information.
        entry_id = record.sub_domain.split(".", 1)[0]
        if entry_id in entries_dict:
            entries_dict[entry_id].record = record
        else:
            entries_dict[entry_id] = Entry(record=record)


def sort_entries(entries_dict: Dict[str, Entry]):
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
        instance = entry.instance
        record = entry.record

        if record:
            # Generate the full domain name for this entry from the domain's info.
            full_domain = "%s.%s" % (record.sub_domain, record.zone)

        if instance is None:
            # We're sure that domain is not None (and therefore full_domain is defined)
            # here because otherwise this ID wouldn't be in the dict.
            orphaned_domains.append([entries_dict, full_domain, record.target])
        elif record is None:
            # We're sure that instance is not None here because otherwise this ID wouldn't
            # be in the dict.
            orphaned_instances.append([
                entries_dict,
                instance.name,
                instance.status,
                instance.ip_address
            ])
        else:
            complete_entries.append([
                entries_dict,
                instance.name,
                full_domain,
                instance.status,
                instance.ip_address,
            ])

    return complete_entries, orphaned_domains, orphaned_instances


def get_list(config) -> Dict[str, Entry]:
    """Retrieve a list of all instances and DNS records under a configured namespace.

    Args:
        config (dict): The parsed configuration.

    Returns:
        A dict containing the entries, looking like

        {
            "<id>": {"instance": ..., "record": ...},
        }

        where "instance" is the instance associated with this ID (an Instance object) and
        "record" is the DNS record associated with this ID (a DNSRecord object).
    """
    # Initialise the empty dict which will be populated later.
    entries_dict = {}

    # Populate the dict with instances.
    gather_instances(entries_dict, config)
    # Populate the dict with DNS records.
    gather_records(entries_dict, config)

    return entries_dict


def get_and_print_list(config):
    """Retrieve a list of all instances and dDNS record under a configured namespace and
    print a table listing them and associating each instance with its domain name.

    If an instance doesn't have a DNS record associated, or vice-versa, the entry is
    listed in one of two extra tables (depending on what is missing). Each of those extra
    tables is only displayed if it contains at least one entry (unless explicitly told not
    to by the command-line arguments).

    Args:
        config (dict): The parsed configuration.
    """
    args = parse_args()

    # Retrieve the list of instances and DNS record.
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
                headers=["Name", "Domain", "Target"],
                tablefmt="psql"
            ))


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party list",
        description="List existing servers.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increases the verbosity."
    )
    parser.add_argument(
        "-H", "--hide-orphans",
        action="store_true",
        help="Hide instances without a domain and domains without an instance. Defaults"
             " to false.",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger("install_party").setLevel(logging.DEBUG)

    return args
