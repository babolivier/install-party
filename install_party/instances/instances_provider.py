import importlib

from install_party.instances.instances_provider_client import InstancesProviderClient
from install_party.util.errors import UnknownProviderError


def get_instances_provider_client(config) -> InstancesProviderClient:
    """Instantiate an API client for the configured instances provider.

    Args:
        config (dict): The parsed configuration.

    Returns:
        The instantiated client.

    Raises:
        UnknownProviderError: The configured instances provider isn't supported.
    """

    provider = config["instances"]["provider"]
    args = config["instances"]["args"]

    try:
        provider_import_path = "install_party.instances.providers.%s" % provider
        provider = importlib.import_module(provider_import_path)

        return provider.provider_client_class(args)
    except ModuleNotFoundError:
        raise UnknownProviderError("Unsupported instances provider %s" % provider)
