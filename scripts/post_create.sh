#!/bin/bash

# Change the SSH auth rules to only allow authentication with password.
sed -i "s/#PubkeyAuthentication yes/PubkeyAuthentication no/" /etc/ssh/sshd_config
sed -i "s/PasswordAuthentication no/PasswordAuthentication yes/" /etc/ssh/sshd_config

# Restart the SSH daemon to apply.
systemctl restart sshd

# Set the password for the user.
echo "{user}:{password}" | chpasswd

# Install Riot.
mkdir -p /var/www
cd /var/www
curl -LO "https://github.com/vector-im/riot-web/releases/download/{riot_version}/riot-{riot_version}.tar.gz"
tar xvf riot-{riot_version}.tar.gz

# Configure Riot.
cat > riot-{riot_version}/config.json <<EOF
{{
  "default_server_config": {{
    "m.homeserver": {{
      "base_url": "https://{expected_domain}:8448",
      "server_name": "{expected_domain}"
    }}
  }}
}}
EOF

# Install Caddy.
curl https://getcaddy.com | bash -s personal

mkdir /etc/ssl/caddy
mkdir /etc/caddy

chown -R www-data:www-data /etc/ssl/caddy
chown -R www-data:www-data /etc/caddy

# Configure Caddy.
cat > /etc/caddy/Caddyfile <<EOF
{expected_domain} {{
  root /var/www/riot-{riot_version}
  proxy /.well-known 127.0.0.1:8888
}}
EOF

# Create a SystemD service for Caddy.
curl "https://raw.githubusercontent.com/caddyserver/caddy/master/dist/init/linux-systemd/caddy.service" > /etc/systemd/system/caddy.service

# Start Caddy.
systemctl start caddy
