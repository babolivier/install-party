# Install Party

This is a project that creates and manages ephemeral servers for install parties/workshops of Matrix homeservers.

## Install and run

Install Party can be installed via `pip`:

```bash
pip install install-party
```

Then it can be run with:

```bash
python -m install_party [mode] [options]
```

## Creation mode

The creation mode (`create`) uses the OpenStack and OVH APIs to create a new host, attach a domain to it, and run a script that installs Riot and Caddy on it, so that an attendee can log in (with SSH) with the configured username and password, install a new homeserver, and directly use it with the Riot instance.

The OpenStack instance name will be `{namespace}-{name}` and the domain name will be `{name}.{namespace}.{zone}`, where:

* `{namespace}` is a configured namespace (e.g. the event's name as a slug)
* `{zone}` is a configured DNS zone (must be managed by OVH)
* `{name}` is the host's name (either provided, e.g. `install_party.py create foo`, or a randomly generated 5-letter string) 

Note: currently, if attendees wish/need to use a homeserver's built-in ACME support, they **must** set the post the ACME support listener is listening to to `8888`.

## List mode

The list mode (`list`) prints a table listing the existing servers and domains under the namespace and DNS zone configured in the configuration file, along with their status.

If an instance has no domain attached, or if a domain isn't attached to an existing instance, they will be listed in separate tables (named `ORPHANED INSTANCES` and `ORPHANED DOMAINS`).

## Configuration

The configuration is provided as a YAML configuration file. By default, a file named `config.yaml` in the current directory will be used, but this can be overridden by setting the environment variable `INSTALL_PARTY_CONFIG` to the path of the desired file.

The configuration file's content must follow the following structure. Currently, all fields are mandatory.

```yaml
# General configuration that's not specific to a section.
general:
  # Namespace to use when creating/listing the instances and DNS records.
  namespace: my-super-event
  # DNS zone to create the DNS records on.
  dns_zone: example.com
  # The version of Riot to install on the hosts.
  riot_version: v1.4.2

# Configuration specific to the instances.
instances:
  # User the attendee will use when logging into the host with SSH.
  # Must already exist on the system.
  user: superevent
  # Password the attendee will use when logging into the host with SSH.
  password: superevent2019

# Configuration to connect to the OVH API.
# See https://api.ovh.com/ for a full documentation.
ovh:
  endpoint: ovh-eu
  application_key: somesecret
  application_secret: somesecret
  consumer_key: somesecret

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