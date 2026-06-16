#!/bin/bash
# Phase 5 PM Routing Stage A - Automated Verification Script
# Verifies that PM identity and boundary rules are properly configured

set -e

echo "=== PM Routing Stage A Verification ==="
echo

# 1. Check systemd WorkingDirectory
echo "1. Checking systemd WorkingDirectory..."
WORKING_DIR=$(grep "^WorkingDirectory=" /etc/systemd/system/cccagents-hermes-gateway.service | cut -d'=' -f2)
if [ "$WORKING_DIR" = "/home/ubuntu/cccagents-source" ]; then
    echo "   ✓ WorkingDirectory is correct: $WORKING_DIR"
else
    echo "   ✗ WorkingDirectory is incorrect: $WORKING_DIR (expected /home/ubuntu/cccagents-source)"
    exit 1
fi
echo

# 2. Check AGENTS.md exists and contains PM identity rules
echo "2. Checking AGENTS.md PM identity rules..."
AGENTS_FILE="/home/ubuntu/cccagents-source/AGENTS.md"
if [ ! -f "$AGENTS_FILE" ]; then
    echo "   ✗ AGENTS.md not found at $AGENTS_FILE"
    exit 1
fi

if grep -q "cccagents PM Agent" "$AGENTS_FILE"; then
    echo "   ✓ AGENTS.md contains PM Agent identity"
else
    echo "   ✗ AGENTS.md missing PM Agent identity"
    exit 1
fi

if grep -q "Gateway boundary" "$AGENTS_FILE"; then
    echo "   ✓ AGENTS.md contains Gateway boundary section"
else
    echo "   ✗ AGENTS.md missing Gateway boundary section"
    exit 1
fi

if grep -q "PM responsibilities" "$AGENTS_FILE"; then
    echo "   ✓ AGENTS.md contains PM responsibilities section"
else
    echo "   ✗ AGENTS.md missing PM responsibilities section"
    exit 1
fi
echo

# 3. Check Hermes config.yaml has agent.system_prompt
echo "3. Checking Hermes config.yaml system_prompt..."
CONFIG_FILE="/home/ubuntu/.hermes/config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "   ✗ config.yaml not found at $CONFIG_FILE"
    exit 1
fi

if grep -q "system_prompt:" "$CONFIG_FILE"; then
    echo "   ✓ config.yaml contains system_prompt"
else
    echo "   ✗ config.yaml missing system_prompt"
    exit 1
fi

if grep -q "cccagents PM Agent" "$CONFIG_FILE"; then
    echo "   ✓ system_prompt mentions cccagents PM Agent"
else
    echo "   ✗ system_prompt missing PM Agent identity"
    exit 1
fi
echo

# 4. Check gateway service is active
echo "4. Checking gateway service status..."
if systemctl is-active --quiet cccagents-hermes-gateway; then
    echo "   ✓ cccagents-hermes-gateway is active"
else
    echo "   ✗ cccagents-hermes-gateway is not active"
    exit 1
fi
echo

# 5. Check Feishu websocket connection
echo "5. Checking Feishu websocket connection..."
GATEWAY_LOG="/home/ubuntu/.hermes/logs/gateway.log"
if [ ! -f "$GATEWAY_LOG" ]; then
    echo "   ✗ gateway.log not found at $GATEWAY_LOG"
    exit 1
fi

if tail -50 "$GATEWAY_LOG" | grep -q "feishu connected"; then
    echo "   ✓ Feishu websocket connected"
else
    echo "   ✗ Feishu websocket not connected"
    exit 1
fi
echo

# 6. Check allowlist configuration
echo "6. Checking allowlist configuration..."
ENV_FILE="/home/ubuntu/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "   ✗ .env not found at $ENV_FILE"
    exit 1
fi

if grep -q "GATEWAY_ALLOW_ALL_USERS=false" "$ENV_FILE"; then
    echo "   ✓ GATEWAY_ALLOW_ALL_USERS is false"
else
    echo "   ✗ GATEWAY_ALLOW_ALL_USERS is not set to false"
    exit 1
fi

if grep -q "FEISHU_ALLOWED_USERS=ou_" "$ENV_FILE"; then
    echo "   ✓ FEISHU_ALLOWED_USERS is configured"
else
    echo "   ✗ FEISHU_ALLOWED_USERS is not configured"
    exit 1
fi
echo

echo "=== All verification checks passed ==="
echo
echo "PM Routing Stage A is properly configured."
echo "Next: Run Feishu smoke tests manually to verify behavior."
