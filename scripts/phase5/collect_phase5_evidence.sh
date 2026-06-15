#!/bin/bash
set -e

PROJECT_ROOT="${PROJECT_ROOT:-/home/ubuntu/cccagents}"
SOURCE_DIR="${SOURCE_DIR:-/home/ubuntu/cccagents-source}"

echo "=== cccagents Phase 5 部署证据收集 ==="
echo "时间: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# 1. 测试通过证据
echo "1. 测试通过证据:"
cd "$SOURCE_DIR"
PYTHONPATH=src .venv/bin/python -m pytest -q tests | tail -1
echo ""

# 2. Smoke 测试证据
echo "2. Smoke 测试证据:"
ls -la "$PROJECT_ROOT/smoke-tests/"
echo ""

# 3. 服务状态证据
echo "3. 服务状态证据:"
systemctl is-active cccagents-hermes-gateway
systemctl is-active cccagents-pm-scheduler
echo ""

# 4. 审批流程证据
echo "4. 审批流程证据:"
if [ -f "$PROJECT_ROOT/projects/phase5-approval-smoke/project-state.json" ]; then
    cat "$PROJECT_ROOT/projects/phase5-approval-smoke/project-state.json" | python3 -m json.tool
fi
echo ""

# 5. 恢复流程证据
echo "5. 恢复流程证据:"
if [ -f "$PROJECT_ROOT/projects/phase5-recovery-test/project-state.json" ]; then
    cat "$PROJECT_ROOT/projects/phase5-recovery-test/project-state.json" | python3 -m json.tool
fi
echo ""

# 6. 密钥扫描证据
echo "6. 密钥扫描证据:"
cd "$SOURCE_DIR"
LEAKED=$(grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-[a-zA-Z0-9]\{20,\}\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]\{20,\}" docs src tests hermes scripts 2>/dev/null | grep -v "\[REDACTED\]" | grep -v "<redacted" | grep -v "secret-value" | grep -v "sk-test" | grep -v "sk-live-secret" | wc -l)
if [ "$LEAKED" -eq 0 ]; then
    echo "✓ 未发现泄露的真实密钥"
else
    echo "✗ 发现 $LEAKED 处可能的密钥泄露"
fi
echo ""

echo "=== 证据收集完成 ==="
