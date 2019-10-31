import ipaddress

import ovh

from install_party.dns.dns_provider_client import DNSProviderClient, DNSRecord


class OvhDNSProviderClient(DNSProviderClient):
    def __init__(self, args):
        self.client = ovh.Client(
            endpoint=args["endpoint"],
            application_key=args["application_key"],
            application_secret=args["application_secret"],
            consumer_key=args["consumer_key"],
        )

    def create_sub_domain(self, sub_domain, target, zone):
        # This will raise an AddressValueError exception if the value isn't an IPv4
        # address.
        ipaddress.IPv4Address(target)

        record = self.client.post(
            "/domain/zone/%s/record" % zone,
            fieldType="A",
            subDomain=sub_domain,
            target=target,
        )

        return DNSRecord(
            record_id=record["id"],
            sub_domain=record["subDomain"],
            target=record["target"],
            zone=record["zone"],
        )

    def get_sub_domains(self, namespace, zone):
        # Retrieve all DNS records which sub domain ends with "." followed by the
        # namespace.
        sub_domain_filter = "%25.{namespace}".format(
            namespace=namespace,
        )

        record_ids = self.client.get(
            "/domain/zone/%s/record?subDomain=%s" % (zone, sub_domain_filter)
        )

        records = []

        for record_id in record_ids:
            record = self.client.get("/domain/zone/%s/record/%s" % (zone, record_id))

            records.append(DNSRecord(
                record_id=record["id"],
                sub_domain=record["subDomain"],
                target=record["target"],
                zone=record["zone"],
            ))

        return records

    def delete_sub_domain(self, record):
        self.client.delete("/domain/zone/%s/record/%s" % (record.zone, record.record_id))

    def commit(self, zone):
        self.client.post("/domain/zone/%s/refresh" % zone)


provider_client_class = OvhDNSProviderClient
