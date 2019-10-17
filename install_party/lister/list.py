from tabulate import tabulate

from install_party.util import openstack, ovh


def gather_instances(entries_dict, config):
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
    complete_entries = []
    orphaned_instances = []
    orphaned_domains = []
    for entries_dict, entry in entries_dict.items():
        instance = entry.get("instance")
        domain = entry.get("domain")

        if domain:
            full_domain = "%s.%s" % (domain["subDomain"], domain["zone"])

        if domain is None:
            # We're sure that instance is not None here because otherwise this ID wouldn't
            # be in the dict.
            orphaned_instances.append([
                entries_dict,
                instance.name,
                instance.status,
                openstack.get_ipv4(instance)
            ])
        elif instance is None:
            # We're sure that domain is not None (and therefore full_domain is defined)
            # here because otherwise this ID wouldn't be in the dict.
            orphaned_domains.append([entries_dict, full_domain, domain["target"]])
        else:
            complete_entries.append([
                entries_dict,
                instance.name,
                full_domain,
                instance.status,
                openstack.get_ipv4(instance)
            ])

    return complete_entries, orphaned_domains, orphaned_instances


def get_and_print_list(config):
    # Initialise the empty dict which will be populated later.
    entries_dict = {}

    # Populate the dict with instances.
    gather_instances(entries_dict, config)
    # Populate the dict with domains.
    gather_domains(entries_dict, config)

    # Sort the entries into three lists.
    complete_entries, orphaned_domains, orphaned_instances = sort_entries(entries_dict)

    # Print the lists.
    print(tabulate(
        complete_entries,
        headers=["Name", "Instance name", "Domain", "Status", "IPv4"],
        tablefmt="psql",
    ))

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
