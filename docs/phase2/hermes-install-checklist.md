# Phase 2 Hermes Install Checklist

Date: 2026-05-19

## Goal

Install NousResearch Hermes Agent on Linux and verify the `hermes` CLI is available.

## Commands

```bash
python3 --version
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes --help
hermes doctor
```

## Evidence

Save command output to:

```text
docs/phase2/linux-ops/hermes-install.log
```

## Secret Rule

Do not write real API keys, Feishu secrets, or tokens into this file or the operation log.
