"""
cccagents Gateway Hook

This hook fires when the Hermes Gateway starts processing a message from Feishu.
It handles:
1. Approval actions (approve/reject/pause/resume) → updates project state
2. S3+ triggers → creates project in pending_approval state
3. S0/S1 tasks → executes with real Claude CLI
"""

import os
import sys
import time
import re
from pathlib import Path

# Add cccagents source to path
CCCAGENTS_SOURCE = "/home/ubuntu/cccagents-source"
if CCCAGENTS_SOURCE not in sys.path:
    sys.path.insert(0, f"{CCCAGENTS_SOURCE}/src")

# S3 complexity keywords
S3_TRIGGERS = ["部署.*生产", "修改.*权限", "删除.*数据", "FEISHU_APP_SECRET", "生产环境", "prod"]

# Approval action patterns
APPROVAL_PATTERN = re.compile(
    r"(approve|reject|pause|resume|同意|拒绝|暂停|恢复)\s+(feishu-[\d_]+|s0-[\d_]+)",
    re.IGNORECASE
)

# Claude API config
CLAUDE_BASE_URL = "https://cccai.store/v1"
CLAUDE_MODEL = "gpt-5.5"


def _load_api_key() -> str:
    """Load API key from .env."""
    env_file = Path("/home/ubuntu/.hermes/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("ANTHROPIC_API_KEY", "")


async def handle(event_type: str, context: dict):
    """Handle agent:start event from Hermes Gateway."""
    try:
        message = context.get("message", "")
        platform = context.get("platform", "unknown")
        user_id = context.get("user_id", "unknown")

        if platform != "feishu" or not message:
            return

        # 1. Check for approval action first
        approval_match = APPROVAL_PATTERN.search(message)
        if approval_match:
            await _handle_approval(approval_match, message, user_id)
            return

        # 2. Check for S3 triggers → pending_approval
        if any(re.search(pattern, message, re.IGNORECASE) for pattern in S3_TRIGGERS):
            await _handle_orchestration(message)
            return

        # 3. All other messages → try real Claude CLI execution
        await _handle_real_execution(message)

    except Exception as e:
        print(f"[cccagents-gateway-hook] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()


async def _handle_real_execution(message: str):
    """Handle task with real Claude CLI execution."""
    from cccagents.orchestrator import OrchestrationRequest
    from cccagents.real_orchestrator import RealExecutor, orchestrate_with_real_executor

    api_key = _load_api_key()
    if not api_key:
        print("[cccagents-gateway-hook] No ANTHROPIC_API_KEY found, skipping real execution", flush=True)
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    project_id = f"s0-{timestamp}"
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    project_root = Path("/home/ubuntu/cccagents/projects")
    project_dir = project_root / project_id

    request = OrchestrationRequest(
        project_id=project_id,
        text=message,
        project_root=project_root,
        now=now_ts,
    )

    executor = RealExecutor(
        model=CLAUDE_MODEL,
        base_url=CLAUDE_BASE_URL,
        api_key=api_key,
    )

    result = orchestrate_with_real_executor(request, executor, now_ts)

    print(
        f"[cccagents-gateway-hook] Real execution {project_id}: "
        f"status={result.get('status')}, complexity={result.get('complexity', 'n/a')}",
        flush=True
    )


async def _handle_orchestration(message: str):
    """Handle S3+ orchestration trigger → pending_approval."""
    from cccagents.project_orchestrator import orchestrate_project
    from cccagents.orchestrator import FakeExecutor, OrchestrationRequest

    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    project_id = f"feishu-{timestamp}"
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    project_root = Path("/home/ubuntu/cccagents/projects")
    project_dir = project_root / project_id

    request = OrchestrationRequest(
        project_id=project_id,
        text=message,
        project_root=project_root,
        now=now_ts,
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now_ts)

    print(
        f"[cccagents-gateway-hook] S3 project {project_id}: "
        f"status={result.get('status')}, complexity={result.get('complexity')}",
        flush=True
    )


async def _handle_approval(match: re.Match, message: str, user_id: str):
    """Handle approval action - update project state."""
    from cccagents.approval_handler import ApprovalRequest, process_approval_action
    from cccagents.feishu_contracts import FeishuSecurityContext

    action_text = match.group(1).lower()
    project_id = match.group(2)

    action_map = {
        "approve": "approve", "同意": "approve",
        "reject": "reject", "拒绝": "reject",
        "pause": "pause", "暂停": "pause",
        "resume": "resume", "恢复": "resume",
    }
    action = action_map.get(action_text, action_text)

    project_root = Path("/home/ubuntu/cccagents/projects")
    project_dir = project_root / project_id

    if not project_dir.exists():
        print(f"[cccagents-gateway-hook] Project {project_id} not found", flush=True)
        return

    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    request = ApprovalRequest(
        project_id=project_id,
        approval_id=f"approval-{int(time.time())}",
        action=action,
        feishu_user_id=user_id,
        feishu_message_id=f"msg-{int(time.time())}",
        timestamp=int(time.time()),
        signature="gateway-hook",
    )

    context = FeishuSecurityContext(
        allowed_approvers={user_id},
        seen_event_ids=set(),
        now=int(time.time()),
        timestamp_window_seconds=300,
        expected_signature="gateway-hook",
    )

    result = process_approval_action(request, context, project_dir, now_ts)

    print(
        f"[cccagents-gateway-hook] Approval for {project_id}: "
        f"action={action}, approved={result.approved}, reason={result.reason}",
        flush=True
    )