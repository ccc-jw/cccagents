# cccagents Deployment Guide (2026-06)

> Concrete, copy-paste-ready deployment runbook distilled from the
> 2026-06-24 green deploy.  Where the older
> `docs/final-new-server-deployment-guide.md` covers the happy path in
> narrative form, this file gives the exact commands that worked in
> practice, including the workarounds for restricted-network environments
> (GitHub/npm/ubuntu mirrors blocked from the target host).

## 0. Pre-flight assumptions

| Item | Value used in the verified deploy |
| --- | --- |
| Server | `113.142.217.41` (NAT-internal `172.16.0.142`), Ubuntu 24.04.1 LTS |
| Public SSH | port `20109` → 22 |
| Public HTTP | port `31351` → 80 |
| Public HTTPS | port `32945` → 443 |
| Domain | `feishu.cccai.store` (A → 113.142.217.41), NS at DNSPod |
| Run user | `ubuntu` (we create it; root was used for initial setup) |
| Hermes env | `/home/ubuntu/.hermes/.env` (chmod 600) |
| Project source | `/home/ubuntu/cccagents-source` |
| Project runtime | `/home/ubuntu/cccagents/projects` |

If your port mappings differ, edit them in step 7 (nginx) and step 12
(health check command).

## 1. One-time server setup

```bash
# 1.1 create the run user
useradd -m -s /bin/bash ubuntu

# 1.2 install system packages (assumes apt; the host is in China so
#     archive.ubuntu.com is unreachable — switch sources first)
cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
sed -i "s|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g" /etc/apt/sources.list.d/ubuntu.sources
apt update
apt install -y curl git build-essential python3 python3-venv python3-pip sshpass nginx openssl
```

The same pattern works for any Ubuntu host in a restricted region: back up
the source list, rewrite URIs to a reachable mirror, then `apt update`.

## 2. Get the source onto the server

GitHub is blocked from the host, so the cleanest path is to bundle locally
and `scp`.  From the development machine:

```bash
tar czf /tmp/cccagents-source.tar.gz \
  --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' \
  --exclude='.claude/worktrees' --exclude='.git' \
  -C /path/to/repo .
scp -P 20109 /tmp/cccagents-source.tar.gz root@host:/tmp/
```

On the server:

```bash
mkdir -p /home/ubuntu/cccagents-source
tar xzf /tmp/cccagents-source.tar.gz -C /home/ubuntu/cccagents-source
chown -R ubuntu:ubuntu /home/ubuntu/cccagents-source
```

## 3. Python virtualenv

```bash
su - ubuntu -c "
  cd /home/ubuntu/cccagents-source
  python3 -m venv .venv
  .venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements-dev.txt
  .venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    requests cryptography
"
```

Run the test suite — expect 154 passed on a clean checkout:

```bash
su - ubuntu -c "cd /home/ubuntu/cccagents-source && PYTHONPATH=src .venv/bin/pytest -q tests"
```

## 4. Claude Code CLI

```bash
npm config set registry https://registry.npmmirror.com
npm install -g @anthropic-ai/claude-code
claude --version   # expect 2.x
```

## 5. Hermes Agent

GitHub `raw.githubusercontent.com` is blocked, so install via PyPI mirror:

```bash
su - ubuntu -c "
  cd /home/ubuntu/cccagents-source
  .venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    hermes-agent
  .venv/bin/hermes version
"
ln -sf /home/ubuntu/cccagents-source/.venv/bin/hermes \
       /home/ubuntu/.local/bin/hermes
```

## 6. Hermes secret/config

```bash
mkdir -p /home/ubuntu/.hermes
chmod 700 /home/ubuntu/.hermes

# Substitute real values — never commit this file.
cat > /home/ubuntu/.hermes/.env <<'EOF'
ANTHROPIC_BASE_URL=https://cccai.store
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_MODEL=gpt-5.5

FEISHU_APP_ID=<app-id>
FEISHU_APP_SECRET=<app-secret>
FEISHU_VERIFICATION_TOKEN=<token>
FEISHU_ENCRYPT_KEY=<encrypt-key>

GATEWAY_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=
EOF
chmod 600 /home/ubuntu/.hermes/.env
chown -R ubuntu:ubuntu /home/ubuntu/.hermes
```

Configure the custom provider:

```bash
cat > /home/ubuntu/.hermes/config.yaml <<'EOF'
model:
  provider: custom:cccai
  base_url: https://cccai.store/v1
  default: gpt-5.5
custom_providers:
  - name: cccai
    provider: custom
    base_url: https://cccai.store/v1
    key_env: ANTHROPIC_API_KEY
    model: gpt-5.5
    api_mode: chat_completions
    models:
      gpt-5.5:
        context_length: 128000
EOF
chmod 600 /home/ubuntu/.hermes/config.yaml
chown ubuntu:ubuntu /home/ubuntu/.hermes/config.yaml
```

Smoke-test the custom provider:

```bash
su - ubuntu -c "
  cd /home/ubuntu/cccagents-source
  set -a && . /home/ubuntu/.hermes/.env && set +a
  .venv/bin/hermes chat --query '只回复 OK' \
    --provider custom:cccai --model gpt-5.5 \
    --toolsets safe --quiet --max-turns 3
"
# expected: OK
```

The note: the bare `http://cccai.store` URL on the gateway side redirects to
`https://cccai.store`, but `claude` / `hermes` clients don't follow the
redirect — set the env var to `https://…` from the start.

## 7. systemd services

Three unit files; generate them with the helper script (it knows the right
template) or copy from `scripts/phase4/install_phase4_services.sh` and edit
`PROJECT_SOURCE` / `PROJECT_ROOT` / `HERMES_ENV` for your host:

```bash
cd /home/ubuntu/cccagents-source
PROJECT_SOURCE=/home/ubuntu/cccagents-source \
PROJECT_ROOT=/home/ubuntu/cccagents/projects \
HERMES_ENV=/home/ubuntu/.hermes/.env \
RUN_USER=ubuntu \
UNIT_DIR=/tmp/cccagents-systemd-units \
./scripts/phase4/install_phase4_services.sh
ls /tmp/cccagents-systemd-units/   # 2 files: cccagents-hermes-gateway, cccagents-pm-scheduler
```

`cccagents-feishu-webhook` is **not** generated by that script — it ships
in this repo as `scripts/phase4/cccagents-feishu-webhook.service`.  Copy
all three into `/etc/systemd/system/`:

```bash
cp /tmp/cccagents-systemd-units/cccagents-hermes-gateway.service \
   /tmp/cccagents-systemd-units/cccagents-pm-scheduler.service \
   /etc/systemd/system/
cp /home/ubuntu/cccagents-source/scripts/phase4/cccagents-feishu-webhook.service \
   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cccagents-hermes-gateway \
                   cccagents-pm-scheduler \
                   cccagents-feishu-webhook
```

Watch the gateway come up:

```bash
journalctl -u cccagents-hermes-gateway -n 50 --no-pager | tail -30
```

It will post-install a few extra Python packages on first start (e.g.
`discord.py[voice]`).  This is harmless; just wait ~30 s.

## 8. nginx + TLS

Generate a self-signed cert for the cutover (replace with acme.sh +
Let's Encrypt once DNSPod token is in hand):

```bash
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/nginx/ssl/feishu.key \
  -out    /etc/nginx/ssl/feishu.crt \
  -subj "/CN=feishu.cccai.store" \
  -addext "subjectAltName=DNS:feishu.cccai.store,DNS:cccai.store"
chmod 600 /etc/nginx/ssl/feishu.key
```

Drop in the reverse-proxy site:

```nginx
# /etc/nginx/sites-available/feishu-cccagents
server {
    listen 80;
    server_name feishu.cccai.store cccai.store;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name feishu.cccai.store cccai.store;

    ssl_certificate     /etc/nginx/ssl/feishu.crt;
    ssl_certificate_key /etc/nginx/ssl/feishu.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /healthz {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhook/feishu {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    location /webhook/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    location / {
        return 404 "not found\n";
        add_header Content-Type text/plain;
    }
}
```

Enable it:

```bash
ln -sf /etc/nginx/sites-available/feishu-cccagents \
       /etc/nginx/sites-enabled/feishu-cccagents
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl enable --now nginx
```

## 9. Periodic health check + self-heal timers

The repo ships four units.  Copy and enable:

```bash
cp /home/ubuntu/cccagents-source/scripts/phase4/cccagents-health-check.{service,timer} \
   /home/ubuntu/cccagents-source/scripts/phase4/cccagents-self-heal.{service,timer} \
   /etc/systemd/system/
touch /var/log/cccagents-health.log /var/log/cccagents-self-heal.log
chmod 644 /var/log/cccagents-health.log /var/log/cccagents-self-heal.log
systemctl daemon-reload
systemctl enable --now cccagents-health-check.timer cccagents-self-heal.timer
systemctl list-timers cccagents-* --no-pager
```

Expected:

```
NEXT                        LEFT  LAST                        PASSED  UNIT
Wed 2026-06-24 14:12:06 …  2m43s Wed 2026-06-24 14:07:06 … 2m16s ago cccagents-health-check.timer
Wed 2026-06-24 14:10:00 …  43s   n/a                         n/a     cccagents-self-heal.timer
```

## 10. End-to-end verification

```bash
# 10.1 webhook health probe
curl -sk -H "Host: feishu.cccai.store" https://127.0.0.1/healthz
# expect: {"ok": true, "upstreams": {...}, "checked_at": "..."}

# 10.2 Feishu URL-verification challenge (encrypted round-trip)
python3 - <<'PY'
import base64, hashlib, os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from urllib.parse import quote
key = os.environ["FEISHU_ENCRYPT_KEY"]
aes = hashlib.sha256(key.encode()).digest()
iv = os.urandom(16)
padder = padding.PKCS7(128).padder()
plain = padder.update(b'{"challenge":"deploy_test"}') + padder.finalize()
ct = Cipher(algorithms.AES(aes), modes.CBC(iv)).encryptor().update(plain) + \
     Cipher(algorithms.AES(aes), modes.CBC(iv)).encryptor().finalize()
print(quote(base64.b64encode(iv + ct).decode()))
PY
# paste into:
curl -sk -H "Host: feishu.cccai.store" \
  "https://127.0.0.1/webhook/feishu?echostr=<paste>&timestamp=x&nonce=y"
# expect: 200 + a base64 ciphertext blob

# 10.3 deploy_verify (the gold standard)
SSHPASS='…' PYTHONPATH=/home/ubuntu/cccagents-source/src \
  /home/ubuntu/cccagents-source/scripts/phase4/deploy_verify.sh \
  --remote root@host 20109
# expect: "DEPLOY VERIFY: PASS"
```

## 11. Post-deploy hardening (not blocking the green path)

- Replace the self-signed cert with acme.sh + Let's Encrypt using DNSPod
  DNS-01 challenge.  See `docs/operations/tls-certificate-renewal.md` (TBD)
  for the step-by-step.
- Set up log rotation for `/var/log/cccagents-*.log` (currently
  append-only; will grow forever).
- Schedule weekly evidence refresh:
  `cron: 0 6 * * 1 /home/ubuntu/cccagents-source/scripts/phase4/collect-evidence.sh`
- Re-key the Feishu app secret after any teammate offboarding.

## 12. Common pitfalls (and the one that bit us)

| Symptom | Cause | Fix |
| --- | --- | --- |
| `hermes: Unknown provider 'custom:cccai'` | `HERMES_HOME` not set when running as root | Set `HERMES_HOME=/home/ubuntu/.hermes` explicitly |
| `claude: gpt-5.5 not found` | `ANTHROPIC_BASE_URL` is `http://` and the gateway 301s to `https://` (curl follows; claude does not) | Use `https://cccai.store` directly |
| nginx fails to bind 443 | systemd launches an orphan nginx already listening on 80/443 | `pkill -9 nginx; systemctl start nginx` |
| `claude_executor.subprocess` AttributeError | An old build was running the legacy HTTP-direct path | Re-run `git pull && tar xf` from the latest source tarball |
| `cffi` ImportError after pip install | Old pip version on the host | `pip install --upgrade pip` first |
| `apt install` hangs on `archive.ubuntu.com` | Mirror not reachable from this region | Use the aliyun mirror (see step 1.2) |

## 13. Where to look when something breaks

- `journalctl -u cccagents-hermes-gateway -n 100` — Hermes Gateway + postinstall
- `journalctl -u cccagents-pm-scheduler -n 100` — PM Scheduler cron
- `journalctl -u cccagents-feishu-webhook -n 100` — webhook ingress
- `journalctl -u nginx -n 100` — TLS termination + reverse proxy
- `/var/log/cccagents-health.log` — every-5-min health check report
- `/var/log/cccagents-self-heal.log` — auto-restart decisions
- `/home/ubuntu/cccagents-source/docs/phase4/linux-ops/` — last evidence dump
