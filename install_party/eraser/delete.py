import argparse

from install_party.dns import dns_provider
from install_party.dns.dns_provider_client import DNSRecord, DNSProviderClient
from install_party.lister.list import get_list
from install_party.util import openstack


def filter_entries_dict(entries_dict, args):
    """Filter the entries dict according to the command-line arguments.

    Args:
        entries_dict (dict): Dict of entries generated by list.get_list
        args (Namespace): The parsed command-line arguments.

    Returns:
        A dict following the same schema and data as the provided one but filtered minus
        the entries that the command-line arguments mandate to remove from it.
    """

    if args.server:
        # Only keep the entries that are in args.server.
        filtered_dict = {k: entries_dict[k] for k in args.server}
    elif args.exclude:
        # Only keep the entries that are in the dict but not in args.exclude. We don't
        # care about args.all because args.exclude can only be provided if args.all was
        # provided (therefore the -a/--all argument is more here to help the user
        # understand how the mode is made to work than to serve an actual function).
        filtered_dict = {
            k: entries_dict[k] for k in set(entries_dict.keys()).difference(args.exclude)
        }
    else:
        filtered_dict = entries_dict

    return filtered_dict


def delete_instance(entry_id, instance, nova_client, dry_run):
    """Delete the provided OpenStack instance using the provided OpenStack Nova client,
    or only print a message if the dry-run mode is on.

    If the deletion failed, just print a line about it.

    Args:
        entry_id (str): The ID of the entry we're deleting the instance of.
        instance (Server): An instance of the OpenStack Nova Server class that represents
            the instance to delete.
        nova_client (Client): The OpenStack Nova client to use to perform the deletion.
        dry_run (bool): Whether we're running in dry-run mode.
    """
    print("Deleting instance for id %s..." % entry_id)

    # Only delete if the dry-run mode is off.
    if not dry_run:
        try:
            nova_client.servers.delete(instance)
        except Exception as e:
            print("Failed to delete instance for %s:" % entry_id, e)


def delete_record(
        entry_id: str,
        record: DNSRecord,
        client: DNSProviderClient,
        dry_run: bool
):
    """Delete the DNS record associated with the provided entry.

    Args:
        entry_id (str): The ID of the entry we're deleting the DNS record of.
        record (DNSRecord): The DNS record to delete.
        client (DNSProviderClient): A client to the DNS provider's API to use to perform
            the deletion.
        dry_run (bool): Whether we're running in dry-run mode.
    """
    print("Deleting domain name for id %s..." % entry_id)

    # Only delete if the dry-run mode is off.
    if not dry_run:
        try:
            client.delete_sub_domain(record)
        except Exception as e:
            print("Failed to delete domain name for %s:" % entry_id, e)


def delete(config):
    """Delete one or several (or all) entries, as defined by the command-line arguments.

    Args:
        config (dict): The parsed configuration.
    """
    args = parse_args()

    # Warn that we're running in dry-run mode if it's the case.
    if args.dry_run:
        print("Running in dry-run mode.")

    # Populate the dict of entries.
    entries_dict = get_list(config)

    # Instantiate the OpenStack and OVH clients.
    nova_client = openstack.get_nova_client(config)
    dns_client = dns_provider.get_dns_provider_client(config)

    # Filter the entries_dict accordingly with the arguments.
    entries_to_delete = filter_entries_dict(entries_dict, args)

    # Loop over the entries to delete and delete them.
    for entry_id, entry in entries_to_delete.items():
        instance = entry.get("instance")
        record = entry.get("record")

        # If we know about an instance for this entry, delete it.
        if instance:
            delete_instance(entry_id, instance, nova_client, args.dry_run)

        # If we know about a DNS record for this entry, delete it.
        if record:
            delete_record(entry_id, record, dns_client, args.dry_run)

    print("Applying the DNS changes...")

    if not args.dry_run:
        # Refresh the DNS server's configuration to make it aware of the changes.
        dns_client.commit(config["dns"]["zone"])

    print("Done!")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party delete",
        description="Delete existing servers.",
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="List the deletions that would normally happen but don't actually perform"
             " them.",
    )
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        metavar="NAME",
        help="Delete all servers which name(s) belong to the configured namespace, except"
             " for the provided name(s) (use it once per name). Can only be used with the"
             " -a/--all argument.",
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-s", "--server",
        action="append",
        metavar="NAME",
        help="Only delete the servers for the provided name(s) instead of all of the"
             " existing ones in the configured namespace (use it once per name)."
    )
    group.add_argument(
        "-a", "--all",
        action="store_true",
        help="Delete all of the servers (except the ones provided with --exclude, if"
             " any)."
    )

    args = parser.parse_args()

    if args.exclude and not args.all:
        parser.error("argument -e/--exclude can only be used with argument -a/--all")

    return args
