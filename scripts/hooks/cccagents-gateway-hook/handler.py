"""
cccagents Gateway Hook

This hook fires when the Hermes Gateway starts processing a message from Feishu.
It detects orchestration triggers (S3 complexity) and creates a project in pending_approval state.
"""

import os
import sys
import time
from pathlib import Path

# Add cccagents source to path
CCCAGENTS_SOURCE = "/home/ubuntu/cccagents-source"
if CCCAGENTS_SOURCE not in sys.path:
    sys.path.insert(0, f"{CCCAGENTS_SOURCE}/src")


async def handle(event_type: str, context: dict):
    """Handle agent:start event from Hermes Gateway."""
    try:
        # Extract message from context
        message = context.get("message", "")
        platform = context.get("platform", "unknown")
        user_id = context.get("user_id", "unknown")

        # Only process Feishu messages
        if platform != "feishu" or not message:
            return

        # Check for orchestration triggers (S3 complexity keywords)
        triggers = ["部署.*生产", "修改.*权限", "删除.*数据", "FEISHU_APP_SECRET", "生产环境", "prod"]
        import re
        if not any(re.search(pattern, message, re.IGNORECASE) for pattern in triggers):
            return

        # Import cccagents modules
        from cccagents.project_orchestrator import orchestrate_project
        from cccagents.orchestrator import FakeExecutor, OrchestrationRequest

        # Generate project ID
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        project_id = f"feishu-{timestamp}"
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        project_root = Path("/home/ubuntu/cccagents/projects")
        project_dir = project_root / project_id

        # Create orchestration request
        request = OrchestrationRequest(
            project_id=project_id,
            text=message,
            project_root=project_root,
            now=now_ts,
        )

        # Run orchestrator
        result = orchestrate_project(project_dir, request, FakeExecutor(), now_ts)

        # Log result (visible in gateway logs)
        print(f"[cccagents-gateway-hook] Created project {project_id}: status={result.get('status')}, complexity={result.get('complexity')}", flush=True)

    except Exception as e:
        # Don't crash the gateway, just log the error
        print(f"[cccagents-gateway-hook] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()