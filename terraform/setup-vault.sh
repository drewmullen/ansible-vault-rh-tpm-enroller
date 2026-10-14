#!/bin/bash
# Install Vault Enterprise on the test instance and leave it unsealed.
# The license file is copied separately to /opt/vault/vault.hclic.
set -euo pipefail

VER='2.2.0-rc1+ent'
PUBLIC_IP="${1:?public ip}"

if ! /usr/local/bin/vault version 2>/dev/null | grep -q "$VER"; then
  dnf install -y unzip curl
  curl -fsSL -o /tmp/vault.zip "https://releases.hashicorp.com/vault/${VER}/vault_${VER}_linux_amd64.zip"
  unzip -o /tmp/vault.zip -d /usr/local/bin
  chmod 0755 /usr/local/bin/vault
  rm -f /tmp/vault.zip
fi

id vault >/dev/null 2>&1 || useradd --system --home-dir /opt/vault --shell /sbin/nologin vault
install -d -o vault -g vault -m 0750 /opt/vault/data /opt/vault/tls /etc/vault.d
install -m 0640 -o vault -g vault /tmp/vault.hclic /opt/vault/vault.hclic
rm -f /tmp/vault.hclic

openssl req -x509 -newkey rsa:2048 \
  -keyout /opt/vault/tls/vault.key \
  -out /opt/vault/tls/vault.crt \
  -days 30 -nodes \
  -subj "/CN=vault-tpm-enroller" \
  -addext "subjectAltName=IP:127.0.0.1,IP:${PUBLIC_IP},DNS:localhost"
chown vault:vault /opt/vault/tls/vault.key /opt/vault/tls/vault.crt
chmod 0640 /opt/vault/tls/vault.key
chmod 0644 /opt/vault/tls/vault.crt

cat >/etc/vault.d/vault.hcl <<'EOF'
storage "file" {
  path = "/opt/vault/data"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/opt/vault/tls/vault.crt"
  tls_key_file  = "/opt/vault/tls/vault.key"
}

api_addr      = "https://127.0.0.1:8200"
disable_mlock = true
license_path  = "/opt/vault/vault.hclic"
EOF
chown root:vault /etc/vault.d/vault.hcl
chmod 0640 /etc/vault.d/vault.hcl

cat >/etc/systemd/system/vault.service <<'EOF'
[Unit]
Description=Vault Enterprise
After=network-online.target
Wants=network-online.target

[Service]
User=vault
Group=vault
ExecStart=/usr/local/bin/vault server -config=/etc/vault.d/vault.hcl
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now vault

export VAULT_ADDR=https://127.0.0.1:8200
export VAULT_CACERT=/opt/vault/tls/vault.crt
for _ in $(seq 1 30); do
  /usr/local/bin/vault status -format=json >/tmp/vault-status.json 2>/tmp/vault-status.err || true
  if python3 -c 'import json; json.load(open("/tmp/vault-status.json"))' 2>/dev/null; then
    break
  fi
  sleep 2
done
python3 -c 'import json; json.load(open("/tmp/vault-status.json"))'

if ! python3 -c 'import json; raise SystemExit(0 if not json.load(open("/tmp/vault-status.json")).get("initialized") else 1)'; then
  echo "already initialized"
else
  /usr/local/bin/vault operator init -key-shares=1 -key-threshold=1 -format=json >/root/vault-init.json
  chmod 0600 /root/vault-init.json
fi

python3 - <<'PY'
import json, subprocess, os
init = json.load(open("/root/vault-init.json"))
env = os.environ.copy()
subprocess.check_call(["/usr/local/bin/vault", "operator", "unseal", init["unseal_keys_b64"][0]], env=env)
env["VAULT_TOKEN"] = init["root_token"]
subprocess.check_call(["/usr/local/bin/vault", "secrets", "enable", "-path=secret", "kv-v2"], env=env)
subprocess.check_call(["/usr/local/bin/vault", "kv", "put", "secret/tpm-test", "message=tpm auth ok"], env=env)
PY

install -m 0600 -o ec2-user -g ec2-user /root/vault-init.json /home/ec2-user/vault-init.json
/usr/local/bin/vault status -format=json | python3 -c 'import json,sys; h=json.load(sys.stdin); print(h.get("version"), "sealed="+str(h.get("sealed")))'
