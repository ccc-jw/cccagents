#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/home/ubuntu/cccagents}"
SOURCE_DIR="${SOURCE_DIR:-/home/ubuntu/cccagents-source}"
HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.hermes/.env}"

cd "$SOURCE_DIR"

export PYTHONPATH="$SOURCE_DIR/src"

echo "=== cccagents Orchestrator Smoke Test ==="
echo "Project root: $PROJECT_ROOT"
echo "Source dir: $SOURCE_DIR"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

SMOKE_DIR="$PROJECT_ROOT/smoke-tests"
mkdir -p "$SMOKE_DIR"

run_smoke() {
    local name="$1"
    local text="$2"
    local expected_complexity="$3"

    echo "--- Running smoke: $name (expected: $expected_complexity) ---"

    python3 - <<PY
import json
from pathlib import Path
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state

project_root = Path("$SMOKE_DIR")
request = OrchestrationRequest(
    project_id="smoke-$name",
    text="$text",
    project_root=project_root,
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)",
)

result = orchestrate_request(request, FakeExecutor())
state = load_project_state(project_root / "smoke-$name")

print(f"Status: {result.status}")
print(f"Complexity: {result.complexity}")
print(f"Executed roles: {result.executed_roles}")
print(f"Issues: {result.issues}")

assert result.status == "done", f"Expected done, got {result.status}"
assert result.complexity == "$expected_complexity", f"Expected $expected_complexity, got {result.complexity}"

print("PASS")
PY

    echo ""
}

run_smoke "s0" "修复 README 里的 typo" "S0"
run_smoke "s1" "修复登录按钮 loading 的局部 bug，并跑本地测试" "S1"
run_smoke "s2" "新增一个导出订单 CSV 的功能，包含接口和测试用例" "S2"

echo "=== Smoke Test Summary ==="
echo "S0: PASS"
echo "S1: PASS"
echo "S2: PASS"
echo ""
echo "All smoke tests completed successfully."
