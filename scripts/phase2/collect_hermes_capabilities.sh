#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-docs/phase2/hermes-capability-report.md}"
mkdir -p "$(dirname "$OUTPUT")"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

{
  printf "# Phase 2 Hermes Capability Report\n\n"
  printf "Generated at: %s\n\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  printf "## hermes version/help\n\n\`\`\`text\n"
  hermes --help || true
  printf "\n\`\`\`\n\n"

  printf "## hermes doctor\n\n\`\`\`text\n"
  hermes doctor || true
  printf "\n\`\`\`\n\n"

  printf "## hermes model\n\n\`\`\`text\n"
  hermes model --help || hermes model || true
  printf "\n\`\`\`\n\n"

  printf "## hermes tools\n\n\`\`\`text\n"
  hermes tools --help || hermes tools || true
  printf "\n\`\`\`\n\n"

  printf "## hermes gateway\n\n\`\`\`text\n"
  hermes gateway --help || true
  printf "\n\`\`\`\n\n"

  printf "## config files\n\n\`\`\`text\n"
  ls -la ~/.hermes || true
  printf "\n\`\`\`\n"
} > "$OUTPUT"
