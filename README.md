# Install Party

![PyPI](https://img.shields.io/pypi/v/install-party?style=flat-square) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/install-party?style=flat-square) [![#install-party:abolivier.bzh on Matrix](https://img.shields.io/matrix/install-party:abolivier.bzh.svg?server_fqdn=matrix.org&logo=matrix&style=flat-square)](https://matrix.to/#/#install-party:abolivier.bzh)

This is a project that creates and manages ephemeral servers for install
parties/workshops of [Matrix](https://matrix.org) homeservers.

## Install and run

Install Party can be installed via `pip`:

```bash
pip install install-party
```

Then it can be run with:

```bash
python -m install_party [mode] [arguments]
```

Every mode can be run with the `-h` argument to display the list of
arguments it supports.

## Creation mode

The creation mode (`create`) uses creates a new server by creating a
new instance (virtual/physical machine), attaching a domain to it, and
runing a script that installs [Riot](https://about.riot.im/) and
[Caddy](https://caddyserver.com/) on it, so that an attendee can log in
(with SSH) with the configured username and password, install a new
homeserver, and directly use it with the Riot instance.

The instance name will be `{namespace}-{name}` and the domain name will
be `{name}.{namespace}.{zone}`, where:

* `{namespace}` is a configured namespace (e.g. the event's name as a slug)
* `{zone}` is a configured DNS zone (must be managed by the configured DNS provider)
* `{name}` is the host's name (either provided, e.g. `install_party create -n/--name foo`, or a randomly generated 5-letter string)

Note: currently, if attendees wish/need to use a homeserver's built-in
ACME support, they must set the post the ACME support listener is
listening to to `8888`.

Creating multiple servers in the same run is possible by using the
command-line argument `-N/--number x` where `x` is the number of servers
to create. If one or more creation(s) failed, Install Party will not
automatically attempt to recreate them.

This mode also accepts the command-line argument
`-s/--post-install-script` that points to a script to run after the
server's creation and its initial setup (i.e. after the installation of
Riot and Caddy).

## List mode

The list mode (`list`) prints a table listing the existing servers and
domains under the namespace and DNS zone configured in the configuration
file, along with their status.

If an instance has no domain attached, or if a domain isn't attached to
an existing instance, they will be listed in separate tables (named
`ORPHANED INSTANCES` and `ORPHANED DOMAINS`). These additional tables
can be hidden by using the command-line flag `-H/--hide-orphans`.

This mode also accepts the command-line argument `-v/--verbose` to print
out additional logging.

## Deletion mode

The deletion mode (`delete`) deletes one or more instance(s) along with
the associated domain name(s). The instances to delete are defined by
the command-line arguments. This mode currently accepts the following
arguments:

* `-a/--all`: delete all instances and domains in the configured namespace. Can't be used together with `-s/--server NAME`.
* `-e/--exclude NAME`: exclude one or more server(s) from the deletion. Can only be used with `-a/--all`. Repeat this argument for every server you want to exclude from the deletion. `NAME` is the name of the server (without the namespace).
* `-s/--server NAME`: only delete this or these server(s). Repeat this argument for every server you want to delete. `NAME` is the name of the server (without the namespace). Can't be used together with `-a/--all`.
* `-d/--dry-run`: run the deletion in dry run mode, i.e. no deletion will actually happen but Install Party will act as if, so that the user can check if it's doing the right thing before performing the actual operation.

One of `-a/--all` or `-s/--server NAME` must be provided.

For example, deleting every server but the ones named `matrixtest1` and
`matrixtest2` would look like this:

```
install_party delete --all --exclude matrixtest1 --exclude matrixtest2
```

On the other hand, deleting only the servers named `matrixtest1` and
`matrixtest2` would look like this:

```
install_party delete --server matrixtest1 --server matrixtest2
```

This mode also accepts the command-line argument `-v/--verbose` to print
out additional logging.

## Configuration

The configuration is provided as a YAML configuration file. By default,
a file named `config.yaml` in the current directory will be used, but
this can be overridden by setting the environment variable
`INSTALL_PARTY_CONFIG` to the path of the desired file.

The configuration file's content must follow the following structure.
Currently, all fields are mandatory.

```yaml
# General configuration that's not specific to a section.
general:
  # Namespace to use when creating/listing the instances and DNS records.
  namespace: my-super-event
  # The version of Riot to install on the hosts.
  riot_version: v1.4.2
  # Maximum number of seconds to seconds to spend on checking if the
  # server is online after its creation. If this duration is reached,
  # the check will be aborted and the creation will be considered a
  # failure. 
  connectivity_check_timeout: 300

# Configuration specific to the instances.
instances:
  # User the attendee will use when logging into the host with SSH.
  # Will be created if it doesn't exist on the system.
  user: superevent
  # Password the attendee will use when logging into the host with SSH.
  password: superevent2019
  # Instances provider to use. Must be a supported provider. See which
  # providers are supported in install_party/instances/providers (there
  # is a file for each supported provider).
  provider: myinstancesprovider
  # Arguments to provide to the instances provider's API client. See the
  # documentation below.
  args:
    arg1: value1
    arg2: value2

# Configuration for connecting to the DNS provider and creating the DNS
# record.
dns:
  # DNS zone to create the DNS records on.
  zone: example.com
  # DNS provider to use. Must be a supported provider. See which
  # providers are supported in install_party/dns/providers (there is a
  # file for each supported provider).
  provider: mydnsprovider
  # Arguments to provide to the DNS provider's API client. See the
  # documentation below.
  args:
    arg1: value1
    arg2: value2
```

## Instances provider

Install Party will use the configured instances provider (if supported)
to provision instances (i.e. virtual/physical machines) for the servers
it creates, and also to list and delete instances.

### Supported providers

Here are the instances providers supported by Install Party, along with
their name (i.e. what to write under `provider` in the configuration
file) and their API client's configuration arguments (i.e. what to write
in `args` in the `instances` section of the configuration file).

#### OpenStack

**Provider name:** `openstack`

**Configuration arguments:**

You first need to create an OpenStack account with your OpenStack
provider (or on your OpenStack cluster if you're self-hosting it).

Then provide the authentication credentials along with the configuration
of the instances to create:

```yaml
# Version of the OpenStack compute API. Currently, only versions 2 and
# above are supported.
api_version: 2
# The URL of the authentication (keystone) endpoint.
auth_url: https://auth.example.com/v2.0/
# The project's tenant name.
tenant_name: somesecret
# The project's tenant identifier.
tenant_id: somesecret
# The project's region.
region_name: SOMEREGION
# The account's username.
username: somesecret
# The account's password.
password: somesecret
# ID of the image to use to create the instances.
image_id: my_super_image
# ID of the flavor to use to create the instances.
flavor_id: my_super_flavor
```

See https://docs.openstack.org/ for a full documentation of OpenStack's
APIs.

### Adding support for an instances provider

To add support for an instances provider, simply add a Python code file
in `install_party/instances/providers` which inherits from the
`install_party.instances.instances_provider.InstancesProviderClient`
class and implements its methods. It must then expose this class in a
variable named `provider_client_class` (i.e. add
`provider_class = MyProviderClient` at the end of the file).

You can then use this provider by providing the name of the Python file
(without the `.py` extension) as the instances provider in the
configuration file. The provided class will be instantiated with the
configured arguments, as a `dict` containing the `args` section of the
`instances` configuration.

## DNS providers

Install Party will use the configured DNS provider (if supported) to
create DNS records for the servers it creates, and also to list and
delete DNS records.

### Supported providers

Here are the DNS providers supported by Install Party, along with their
name (i.e. what to write under `provider` in the configuration file) and
their API client's configuration arguments (i.e. what to write in `args`
in the `dns` section of the configuration file).

#### OVH

**Provider name:** `ovh`

**Configuration arguments:**

You first need to create an app on the OVH library to use this provider,
see https://docs.ovh.com/gb/en/customer/first-steps-with-ovh-api/ for
more information. If you want to limit the app's access, you can
restrict it to use only the methods `GET`, `POST` and `DELETE` on the
routes `/domain/zone/*`.

Then provide your app's application key, application secret key and
consumer key (along with the API endpoint to use):

```yaml
endpoint: ovh-eu
application_key: SOME_KEY
application_secret: SOME_SECRET
consumer_key: SOME_KEY
```

### Adding support for a DNS provider

To add support for a DNS provider, simply add a Python code file in
`install_party/dns/providers` which inherits from the
`install_party.dns.dns_provider.DNSProviderClient` class and implements
its methods. It must then expose this class in a variable named
`provider_client_class` (i.e. add `provider_class = MyProviderClient` at
the end of the file).

You can then use this provider by providing the name of the Python file
(without the `.py` extension) as the DNS provider in the configuration
file. The provided class will be instantiated with the configured
arguments, as a `dict` containing the `args` section of the `dns`
configuration.
