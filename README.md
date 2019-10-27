# Install Party

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

The creation mode (`create`) uses the OpenStack and OVH APIs to create a
new host, attach a domain to it, and run a script that installs
[Riot](https://github.com/vector-im/riot-web) and
[Caddy](https://caddyserver.com/) on it, so that an attendee can log in
(with SSH) with the configured username and password, install a new
homeserver, and directly use it with the Riot instance.

The OpenStack instance name will be `{namespace}-{name}` and the domain name will be `{name}.{namespace}.{zone}`, where:

* `{namespace}` is a configured namespace (e.g. the event's name as a slug)
* `{zone}` is a configured DNS zone (must be managed by OVH)
* `{name}` is the host's name (either provided, e.g. `install_party create --name foo`, or a randomly generated 5-letter string)

Note: currently, if attendees wish/need to use a homeserver's built-in
ACME support, they must set the post the ACME support listener is
listening to to `8888`.

Creating multiple servers in the same run is possible by using the
command-line argument `-N x` where `x` is the number of servers to
create. If one or more creation(s) failed, Install Party will not
automatically attempt to recreate them.

## List mode

The list mode (`list`) prints a table listing the existing servers and
domains under the namespace and DNS zone configured in the configuration
file, along with their status.

If an instance has no domain attached, or if a domain isn't attached to
an existing instance, they will be listed in separate tables (named
`ORPHANED INSTANCES` and `ORPHANED DOMAINS`). These additional tables
can be hidden by using the command-line flag `--hide-orphans`.

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

# Configuration to connect to the OVH API.
# See https://api.ovh.com/ for a full documentation.

# Configuration for connecting to the DNS provider and creating the DNS
# record.
dns:
  # DNS zone to create the DNS records on.
  zone: example.com
  # DNS provider to use. Must be a supported provider. See which
  # providers are supported in install_party/dns/providers (there is a
  # file for each supported provider.
  provider: ovh
  # Arguments to provide to the DNS provider's API client.
  args:
    endpoint: ovh-eu
    application_key: SOME_KEY
    application_secret: SOME_SECRET
    consumer_key: SOME_KEY

# Configuration to connect to the OpenStack API or that is using notions
# specific to OpenStack.
# See https://docs.openstack.org/ for a full documentation.
openstack:
  # Version of the OpenStack compute API. Currently, only versions 2 and
  # above are supported.
  api_version: 2
  auth_url: https://auth.example.com/v2.0/
  tenant_name: somesecret
  tenant_id: somesecret
  username: somesecret
  password: somesecret
  region_name: GRA3
  # ID of the image to use to create the instances.
  image_id: my_super_image
  # ID of the flavor to use to create the instances.
  flavor_id: my_super_flavor
```

## DNS providers

Install Party will use the configured DNS provider (if supported) to
create DNS records for the servers it creates, and also to list and
delete DNS records.

### Supported providers

Here are the DNS providers supported by Install Party, along with their
name (i.e. what to write under `provider` in the configuration file) and
their API client's configuration arguments (i.e. what to write in `args`
in the configuration file).

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
file.

## Limitations

As pointed out above, Install Party is designed to only work with
infrastructure projects managed by an OpenStack provider. There is
currently no plan to expand this list of providers.
