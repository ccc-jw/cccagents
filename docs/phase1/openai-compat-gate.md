# Phase 1B OpenAI-Compatible Gate

This is the project stop/go gate.

Pass only if Claude Code CLI itself can directly use all of these values without a protocol adapter:

- `base_url`
- `api_key`
- `model`

Fail if any of these is required:

- Anthropic-only protocol
- Claude official model only
- Protocol adapter
- Replacement executor
- Split model source where Claude Code CLI uses a different provider

Evidence to save:

- Claude Code CLI version
- Install source
- Help/config output showing supported configuration
- Redacted configuration snippet
- Command used for the verification run
- Gateway access evidence
- Output artifact path
- Final decision: `pass` or `fail`

Environment variable verification:

```bash
export ANTHROPIC_BASE_URL="http://cccai.store"
export ANTHROPIC_API_KEY="<redacted-api-key>"
export ANTHROPIC_MODEL="gpt-5.5"

claude -p "只回复 OK" --model gpt-5.5 --output-format text
```

Expected output:

```text
OK
```

Security rule:

- Never commit or paste the real API key into docs, logs, Feishu messages, or prompt summaries.
- Store evidence with `ANTHROPIC_API_KEY=[REDACTED]`.
