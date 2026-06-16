#!/usr/bin/env bash
# cccagents orchestrator hook - injects project context when orchestration is detected
# Receives JSON payload via stdin, returns context injection JSON

set -e

# Read stdin payload
payload="$(cat -)"

# Extract message content from payload
# pre_llm_call payload has: {"session_key": "..., "message": "...", ...}
message=$(echo "$payload" | jq -r '.message // empty')
session_key=$(echo "$payload" | jq -r '.session_key // empty')

# If no message, skip
if [ -z "$message" ]; then
    printf '{}\n'
    exit 0
fi

# Check for orchestration keywords (S3 triggers)
if echo "$message" | grep -qiE '部署.*生产|修改.*权限|删除.*数据|FEISHU_APP_SECRET|生产环境|prod'; then
    # Create project via Python orchestrator
    project_root="/home/ubuntu/cccagents/projects"
    timestamp=$(date -u +%Y%m%d_%H%M%S)
    project_id="feishu-${timestamp}"
    now_ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Call project_orchestrator to create the project
    cd /home/ubuntu/cccagents-source
    result=$(PYTHONPATH=src .venv/bin/python -c "
from pathlib import Path
from cccagents.project_orchestrator import orchestrate_project
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest

project_dir = Path('${project_root}/${project_id}')
request = OrchestrationRequest(
    project_id='${project_id}',
    text='${message}',
    project_root=Path('${project_root}'),
    now='${now_ts}',
)

result = orchestrate_project(project_dir, request, FakeExecutor(), '${now_ts}')
print('status=' + result['status'] + ', complexity=' + result.get('complexity', 'unknown'))
")

    # Inject context for PM Agent
    context="【cccagents 编排器】已识别为高风险请求，项目已创建：
- 项目ID: ${project_id}
- 状态: pending_approval
- 需要用户审批后继续执行

请告知用户此操作需要审批，询问是否继续。"

    jq --null-input --arg ctx "$context" '{context: $ctx}'
else
    # Not an orchestration trigger, skip injection
    printf '{}\n'
fi