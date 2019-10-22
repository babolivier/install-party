from install_party.dns.dns_provider_client import DNSProviderClient
from install_party.util.errors import UnknownProviderError


def get_dns_provider_client(config) -> DNSProviderClient:
    """Instantiate an API client for the configured DNS provider.

    Args:
        config (dict): The parsed configuration.

    Returns:
        The instantiated client.

    Raises:
        UnknownProviderError: The configured DNS provider isn't supported.
    """

    provider = config["dns"]["provider"]
    args = config["dns"]["args"]

    if provider == "ovh":
        from install_party.dns.ovh import OvhDNSProviderClient
        return OvhDNSProviderClient(args)
    else:
        raise UnknownProviderError("Unsupported DNS provider %s" % provider)

