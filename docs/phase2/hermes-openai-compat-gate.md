# Phase 2 Hermes OpenAI Compatibility Gate

Date: 2026-05-19

## Result

Status: pass

Hermes itself can use the user OpenAI-compatible model endpoint after setting the custom provider base URL to include the `/v1` suffix:

```text
model.provider = custom
model.base_url = http://cccai.store/v1
model.default = qwen3.6-plus
```

## Evidence

- Config path: `~/.hermes/config.yaml`
- Secret path: `~/.hermes/.env`
- Initial failed evidence: `docs/phase2/linux-ops/hermes-openai-compat.log`
- Passing retry evidence: `docs/phase2/linux-ops/hermes-openai-v1-retry.log`

## Verification Command

```bash
hermes chat --query "只回复 OK" --provider custom --model qwen3.6-plus --toolsets safe --quiet --max-turns 3
```

Expected output:

```text
OK
```

Actual output:

```text
OK
```

## Conclusion

The earlier failure was caused by using `http://cccai.store` as Hermes `model.base_url`. Hermes requires the OpenAI-compatible API base URL, so `http://cccai.store/v1` is the correct value.

Phase 2 model gate is passed. Phase 2 may continue to Hermes role definition and local no-Feishu PM -> DEV loop.

## Secret Rule

The real API key is stored only in `~/.hermes/.env` on the Linux host. Repository evidence contains only redacted logs and config shape.
