#!/usr/bin/env bash
# cccagents 服务健康检查
#
# 验证所有 systemd 服务 + 端口监听 + 反代链路 + 网关连通性。
# 输出 PASS/FAIL 汇总到 stdout，并把详细日志写入 LOG_FILE。
#
# 用法：
#   ./scripts/phase4/health_check.sh                          # 检查本机
#   ./scripts/phase4/health_check.sh --remote user@host       # 检查远程主机
#   LOG_FILE=/var/log/cccagents/health.log ./scripts/phase4/health_check.sh
#
# 退出码：
#   0 = 全部通过
#   1 = 有失败项
#   2 = 环境前置缺失（如缺少 sshpass、systemctl）
set -uo pipefail

# ---------- 配置 ----------
SSH_TARGET="${SSH_TARGET:-}"
SSH_PORT="${SSH_PORT:-22}"
SSHPASS="${SSHPASS:-}"
if [ "${1:-}" = "--remote" ] && [ -n "${2:-}" ]; then
  SSH_TARGET="$2"
  if [ -n "${3:-}" ]; then
    SSH_PORT="$3"
  fi
fi

LOG_FILE="${LOG_FILE:-/tmp/cccagents-health.log}"
PROJECT_SOURCE="${PROJECT_SOURCE:-/home/ubuntu/cccagents-source}"
PROJECT_ROOT="${PROJECT_ROOT:-/home/ubuntu/cccagents/projects}"
HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.hermes/.env}"
HERMES_BIN="${HERMES_BIN:-/home/ubuntu/.local/bin/hermes}"
WEBHOOK_PORT="${WEBHOOK_PORT:-8080}"
GATEWAY_URL="${GATEWAY_URL:-https://cccai.store/v1/models}"

SERVICES=(
  cccagents-hermes-gateway
  cccagents-pm-scheduler
  cccagents-feishu-webhook
  nginx
)

# ---------- 工具函数 ----------
log() { printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2"; }
pass() { log "PASS" "$1"; printf '  \xe2\x9c\x94 %s\n' "$1"; }
fail() { log "FAIL" "$1"; printf '  \xe2\x9c\x97 %s\n' "$1"; FAILED=1; }
info() { log "INFO" "$1"; printf '  \xe2\x96\xb6 %s\n' "$1"; }

FAILED=0
mkdir -p "$(dirname "$LOG_FILE")"
{
  echo "============================================"
  echo "cccagents Health Check"
  echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Host: $(hostname 2>/dev/null || echo 'unknown')"
  echo "Target: ${SSH_TARGET:-localhost}"
  echo "============================================"
} > "$LOG_FILE"

# ---------- 命令执行 ----------
run() {
  if [ -z "$SSH_TARGET" ]; then
    bash -c "$1"
  else
    sshpass -p "$SSHPASS" ssh -p "$SSH_PORT" \
      -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password -o PubkeyAuthentication=no \
      "$SSH_TARGET" "$1"
  fi
}

# ---------- 前置检查 ----------
info "Environment preflight"
if [ -n "$SSH_TARGET" ] && ! command -v sshpass >/dev/null 2>&1; then
  fail "sshpass not installed (required for --remote)"
  exit 2
fi

if [ -z "$SSH_TARGET" ]; then
  if ! command -v systemctl >/dev/null 2>&1; then
    fail "systemctl not found (not a systemd host?)"
    exit 2
  fi
  if ! command -v ss >/dev/null 2>&1; then
    fail "ss not found (install iproute2)"
    exit 2
  fi
fi

# ---------- 1. systemd 服务状态 ----------
info "systemd service status"
for svc in "${SERVICES[@]}"; do
  enabled="$(run "systemctl is-enabled $svc 2>/dev/null" || echo 'unknown')"
  active="$(run "systemctl is-active $svc 2>/dev/null" || echo 'unknown')"
  if [ "$enabled" = "enabled" ] && [ "$active" = "active" ]; then
    pass "service $svc: $enabled / $active"
  else
    fail "service $svc: $enabled / $active (expected enabled/active)"
  fi
done

# ---------- 2. 端口监听 ----------
info "Port listeners"
check_port() {
  local label="$1" port="$2"
  if run "ss -tln 2>/dev/null | grep -q ':$port '" >/dev/null 2>&1; then
    pass "port $port ($label): listening"
  else
    fail "port $port ($label): not listening"
  fi
}
check_port "feishu webhook" "$WEBHOOK_PORT"
check_port "nginx http" 80
check_port "nginx https" 443

# ---------- 3. 本地 webhook 端点 ----------
info "Local webhook endpoint"
WEBHOOK_LOCAL="$(run "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:$WEBHOOK_PORT/ 2>/dev/null" || echo '000')"
if [ "$WEBHOOK_LOCAL" = "200" ]; then
  pass "GET 127.0.0.1:$WEBHOOK_PORT/ → 200"
else
  fail "GET 127.0.0.1:$WEBHOOK_PORT/ → $WEBHOOK_LOCAL (expected 200)"
fi

WEBHOOK_POST="$(run "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 -X POST http://127.0.0.1:$WEBHOOK_PORT/webhook/feishu -H 'Content-Type: application/json' -d '{\"schema\":\"2.0\",\"header\":{\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_healthcheck\"}},\"message\":{\"message_id\":\"om_healthcheck\",\"chat_id\":\"oc_healthcheck\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"healthcheck\\\"}\"},\"create_time\":\"1700000000\"}}' 2>/dev/null" || echo '000')"
# 200 = fully accepted, 400 = dispatched but business-rejected (e.g. allowlist),
# either proves the webhook server is alive and routing events.
case "$WEBHOOK_POST" in
  200|400)
    pass "POST 127.0.0.1:$WEBHOOK_PORT/webhook/feishu → $WEBHOOK_POST (200=accepted, 400=business-rejected)"
    ;;
  *)
    fail "POST 127.0.0.1:$WEBHOOK_PORT/webhook/feishu → $WEBHOOK_POST (expected 200 or 400)"
    ;;
esac

# ---------- 4. nginx 反代 ----------
info "nginx reverse proxy"
NGINX_HTTP="$(run "curl -sS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:80/ 2>/dev/null" || echo '000')"
case "$NGINX_HTTP" in
  301|302|404)
    pass "GET 127.0.0.1:80/ → $NGINX_HTTP (301/302 = redirect, 404 = routed but / unmatched)"
    ;;
  *)
    fail "GET 127.0.0.1:80/ → $NGINX_HTTP (expected 301/302/404)"
    ;;
esac

NGINX_HTTPS_CODE="$(run "curl -sSk -o /dev/null -w '%{http_code}' --max-time 5 https://127.0.0.1:443/ 2>/dev/null" || echo '000')"
case "$NGINX_HTTPS_CODE" in
  301|302|404)
    pass "GET 127.0.0.1:443/ → $NGINX_HTTPS_CODE (nginx TLS handshake OK)"
    ;;
  *)
    fail "GET 127.0.0.1:443/ → $NGINX_HTTPS_CODE (expected 301/302/404)"
    ;;
esac

NGINX_PROXY="$(run "curl -sSk -o /dev/null -w '%{http_code}' --max-time 5 -X POST https://127.0.0.1:443/webhook/feishu -H 'Content-Type: application/json' -d '{\"schema\":\"2.0\",\"header\":{\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_healthcheck\"}},\"message\":{\"message_id\":\"om_healthcheck\",\"chat_id\":\"oc_healthcheck\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"healthcheck\\\"}\"},\"create_time\":\"1700000000\"}}' 2>/dev/null" || echo '000')"
case "$NGINX_PROXY" in
  200|400)
    pass "POST 127.0.0.1:443/webhook/feishu → $NGINX_PROXY (nginx → 8080 reverse proxy works)"
    ;;
  *)
    fail "POST 127.0.0.1:443/webhook/feishu → $NGINX_PROXY (expected 200 or 400)"
    ;;
esac

# ---------- 5. 网关连通性 ----------
info "Gateway reachability ($GATEWAY_URL)"
# /v1/models 不带 token 时通常返回 401/403（这是预期的），所以 200/401/403 算通过
GW_HTTP="$(run "curl -sS -o /dev/null -w '%{http_code}' --max-time 8 $GATEWAY_URL 2>/dev/null" || echo '000')"
case "$GW_HTTP" in
  200|401|403)
    pass "Gateway $GATEWAY_URL → $GW_HTTP (200 = with key, 401/403 = needs auth)"
    ;;
  *)
    fail "Gateway $GATEWAY_URL → $GW_HTTP (expected 200/401/403)"
    ;;
esac

# ---------- 6. Claude CLI ----------
info "Claude Code CLI"
CLAUDE_VER="$(run "command -v claude >/dev/null 2>&1 && claude --version 2>/dev/null || echo missing")"
if [ "$CLAUDE_VER" != "missing" ] && [ -n "$CLAUDE_VER" ]; then
  pass "claude CLI: $CLAUDE_VER"
else
  fail "claude CLI not installed"
fi

# ---------- 7. Hermes 二进制 ----------
info "Hermes binary"
if run "test -x $HERMES_BIN" >/dev/null 2>&1; then
  HERMES_VER="$(run "$HERMES_BIN version 2>/dev/null" | head -1 || echo 'unknown')"
  pass "Hermes at $HERMES_BIN: $HERMES_VER"
else
  fail "Hermes binary missing at $HERMES_BIN"
fi

# ---------- 8. Hermes chat 端到端 ----------
info "Hermes chat end-to-end"
if run "test -f $HERMES_ENV" >/dev/null 2>&1; then
  # Hermes reads config from $HERMES_HOME/config.yaml (defaults to $HOME/.hermes).
  # When running as root, $HOME=/root and Hermes looks in the wrong place, so
  # we MUST set HERMES_HOME=/home/ubuntu/.hermes BEFORE sourcing the env file.
  CHAT_OUT="$(run "cd $PROJECT_SOURCE && export HERMES_HOME=/home/ubuntu/.hermes && export HOME=/home/ubuntu && set -a && . $HERMES_ENV && set +a && $HERMES_BIN chat --query '只回复 OK' --provider custom:cccai --model gpt-5.5 --toolsets safe --quiet --max-turns 3 2>&1 | tail -3" 2>&1)" || CHAT_OUT="FAILED"
  if echo "$CHAT_OUT" | grep -q 'OK'; then
    pass "Hermes chat returned OK"
  else
    fail "Hermes chat did not return OK (output: ${CHAT_OUT:0:200})"
  fi
else
  info "skipping Hermes chat (env missing)"
fi

# ---------- 9. env 关键变量 ----------
info "Hermes env critical vars"
if run "test -f $HERMES_ENV" >/dev/null 2>&1; then
  ENV_OUTPUT="$(run "cat $HERMES_ENV 2>/dev/null")"
  for var in ANTHROPIC_BASE_URL ANTHROPIC_API_KEY FEISHU_APP_ID FEISHU_VERIFICATION_TOKEN FEISHU_ENCRYPT_KEY; do
    if echo "$ENV_OUTPUT" | grep -q "^$var=.\+"; then
      pass "env $var: set"
    else
      fail "env $var: missing or empty"
    fi
  done
else
  info "skipping env check (file missing: $HERMES_ENV)"
fi

# ---------- 10. 磁盘 / 内存 ----------
info "Disk and memory"
DISK_USED="$(run "df / 2>/dev/null | awk 'NR==2 {sub(/%/,\"\",\$5); print \$5}'" 2>/dev/null)"
if [ -n "$DISK_USED" ] && [ "$DISK_USED" -lt 85 ] 2>/dev/null; then
  pass "disk /: ${DISK_USED}% used"
else
  fail "disk /: ${DISK_USED:-unknown}% used (>= 85%)"
fi

MEM_FREE_MB="$(run "free -m 2>/dev/null | awk 'NR==2 {print \$7}'" 2>/dev/null)"
if [ -n "$MEM_FREE_MB" ] && [ "$MEM_FREE_MB" -gt 512 ] 2>/dev/null; then
  pass "memory: ${MEM_FREE_MB}MB free"
else
  fail "memory: ${MEM_FREE_MB:-unknown}MB free (< 512MB)"
fi

# ---------- 汇总 ----------
echo ""
echo "============================================"
if [ "$FAILED" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
  log "PASS" "all checks passed"
else
  echo "SOME CHECKS FAILED"
  log "FAIL" "one or more checks failed"
fi
echo "Detailed log: $LOG_FILE"
echo "============================================"

exit "$FAILED"