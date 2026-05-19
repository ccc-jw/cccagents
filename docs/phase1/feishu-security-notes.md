# Feishu Security Notes

Phase 3 must verify:

- Event callback signature verification
- Timestamp validation window
- Replay attack protection
- Feishu user id to approver mapping
- Approval action authorization
- No secret values in card content

Feishu is an entry and approval channel, not the source of truth. Hermes state remains authoritative.
