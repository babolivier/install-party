def get_dns_provider_client(config):
    provider = config["dns"]["provider"]
    args = config["dns"]["args"]

    if provider == "ovh":
        from install_party.dns.ovh import OvhDNSProviderClient
        return OvhDNSProviderClient(args)
