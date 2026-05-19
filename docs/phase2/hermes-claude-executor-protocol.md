# Hermes to Claude Code CLI Executor Protocol

Date: 2026-05-19

## Request

```text
project_id
task_id
run_id
agent_role
phase
cwd
prompt
allowed_tools
permission_mode
env_refs
```

## Environment Mapping

```text
model_base_url -> ANTHROPIC_BASE_URL
resolved model_api_key_ref -> ANTHROPIC_API_KEY
model_name -> ANTHROPIC_MODEL
```

## Command

```bash
claude -p "$PROMPT" --model "$ANTHROPIC_MODEL" --output-format text
```

## Path Rule

`cwd` must be inside one of:

```text
workspaces/<project_id>/repo/
projects/<project_id>/
```

## Audit Rule

Each execution writes a record to:

```text
projects/<project_id>/08-logs/command-log.jsonl
```

and detailed run files to:

```text
projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

## Secret Rule

真实 API Key 不得写入 repository files, project artifacts, command-log.jsonl, Hermes prompts, Feishu messages, stdout logs, or stderr logs. Store only `model_api_key_ref` and redacted evidence.
