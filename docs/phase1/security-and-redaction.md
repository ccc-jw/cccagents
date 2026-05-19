# Security and Redaction

Rules:

- Store model secrets by reference as `model_api_key_ref`.
- Do not write API keys into command logs.
- Do not write API keys into artifacts.
- Do not show secrets in Feishu messages.
- Redact stdout and stderr before storing normal logs.

Initial redaction patterns:

- `Bearer <token>`
- `<NAME>API_KEY=<value>`
- `password=<value>`

If a secret is detected:

- Store the redacted text.
- Set `redacted=true`.
- Store `redaction_reason`.
- Do not send the raw content to Feishu.
