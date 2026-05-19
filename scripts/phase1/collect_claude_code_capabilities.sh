#!/usr/bin/env bash
set -euo pipefail

REPORT_PATH="${1:-docs/phase1/phase1b-capability-report.md}"
mkdir -p "$(dirname "$REPORT_PATH")"

{
  echo "# Phase 1B Claude Code CLI Capability Report"
  echo
  echo "## System"
  echo
  echo '```text'
  date -u +%Y-%m-%dT%H:%M:%SZ
  uname -a
  echo '```'
  echo
  echo "## Claude Code Version"
  echo
  echo '```text'
  claude --version || true
  echo '```'
  echo
  echo "## Claude Help"
  echo
  echo '```text'
  claude --help || true
  echo '```'
  echo
  echo "## OpenAI-Compatible Gate Checklist"
  echo
  echo "- [ ] Found native base_url configuration"
  echo "- [ ] Found native api_key configuration"
  echo "- [ ] Found native model configuration"
  echo "- [ ] Verified request reached OpenAI-compatible gateway"
  echo "- [ ] No protocol adapter used"
  echo
  echo "## Decision"
  echo
  echo "Status: pending"
} > "$REPORT_PATH"

printf 'Wrote %s\n' "$REPORT_PATH"
