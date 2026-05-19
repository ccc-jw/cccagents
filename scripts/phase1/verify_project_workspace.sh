#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?project_id required}"
ROOT="${2:-$HOME/cccagents}"

mkdir -p "$ROOT/workspaces/$PROJECT_ID/repo"
mkdir -p "$ROOT/projects/$PROJECT_ID/08-logs/agent-runs"

test -d "$ROOT/workspaces/$PROJECT_ID/repo"
test -d "$ROOT/projects/$PROJECT_ID/08-logs"

printf 'workspace=%s\n' "$ROOT/workspaces/$PROJECT_ID/repo"
printf 'project=%s\n' "$ROOT/projects/$PROJECT_ID"
