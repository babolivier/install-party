import argparse

from install_party.lister.list import get_list
from install_party.util import openstack, ovh


def filter_entries_dict(entries_dict, args):
    """Filter the entries dict according to the command-line arguments.

    Args:
        entries_dict (dict): Dict of entries generated by list.get_list
        args (Namespace): The parsed command-line arguments.

    Returns:
        A dict following the same schema and data as the provided one but filtered minus
        the entries that the command-line arguments mandate to remove from it.
    """

    if args.instance:
        filtered_dict = {k: entries_dict[k] for k in args.instance}
    elif args.exclude:
        # Only keep the entries that are in the dict but not in args.exclude.
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


def delete_record(entry_id, record, ovh_client, config, dry_run):
    """Delete the DNS record associated with the provided entry.

    Args:
        entry_id (str): The ID of the entry we're deleting the instance of.
        record (dict): A dict containing the response to
            https://api.ovh.com/console/#/domain/zone/%7BzoneName%7D/record/%7Bid%7D#GET
        ovh_client (Client): The OVH client to use to perform the deletion.
        config (dict): The parsed configuration.
        dry_run (bool): Whether we're running in dry-run mode.
    """
    print("Deleting domain name for id %s..." % entry_id)

    # Only delete if the dry-run mode is off.
    if not dry_run:
        record_id = record["id"]
        try:
            ovh_client.delete(
                "/domain/zone/%s/record/%s" % (
                    config["general"]["dns_zone"], record_id,
                )
            )
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
    ovh_client = ovh.get_ovh_client(config)

    # Filter the entries_dict accordingly with the arguments.
    entries_to_delete = filter_entries_dict(entries_dict, args)

    # Loop over the entries to delete and delete them.
    for entry_id, entry in entries_to_delete.items():
        instance = entry.get("instance")
        record = entry.get("domain")

        # If we know about an instance for this entry, delete it.
        if instance:
            delete_instance(entry_id, instance, nova_client, args.dry_run)

        # If we know about a domain name for this entry, delete it.
        if record:
            delete_record(entry_id, record, ovh_client, config, args.dry_run)

    print("Refreshing the DNS zone...")

    if not args.dry_run:
        # Refresh the DNS server's configuration to make it aware of the changes.
        ovh_client.post("/domain/zone/%s/refresh" % config["general"]["dns_zone"])

    print("Done!")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install_party delete",
        description="Delete existing instances and domains.",
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="List the deletions that would normally happen but don't actually perform"
             " them.",
    )
    parser.add_argument(
        "-i", "--instance",
        action="append",
        help="Only delete the instances and domains for the provided ID(s) instead of all"
             " of the existing ones in the configured namespace (use it once per ID)."
    )
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        help="Delete all instances and domains which ID(s) belong to the configured"
             " namespace, except for the provided ID(s) (use it once per ID).",
    )

    return parser.parse_args()
