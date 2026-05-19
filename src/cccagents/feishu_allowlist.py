from dataclasses import dataclass


@dataclass(frozen=True)
class FeishuAllowlistDecision:
    allowed: bool
    reason: str
    redacted_user_id: str


@dataclass(frozen=True)
class FeishuAllowlist:
    allowed_user_ids: set[str]
    allow_all_users: bool = False

    def decide(self, user_id: str) -> FeishuAllowlistDecision:
        redacted_user_id = redact_feishu_user_id(user_id)
        if self.allow_all_users:
            return FeishuAllowlistDecision(True, "open_access", redacted_user_id)
        if user_id in self.allowed_user_ids:
            return FeishuAllowlistDecision(True, "allowed_user", redacted_user_id)
        return FeishuAllowlistDecision(False, "user_not_allowlisted", redacted_user_id)


def redact_feishu_user_id(user_id: str) -> str:
    if user_id.startswith("ou_"):
        return "ou_***"
    if len(user_id) <= 4:
        return "***"
    return f"{user_id[:2]}***"


def validate_phase4_allowlist(allowlist: FeishuAllowlist) -> None:
    if allowlist.allow_all_users:
        raise ValueError("GATEWAY_ALLOW_ALL_USERS is not allowed in Phase 4")
    if not allowlist.allowed_user_ids:
        raise ValueError("Phase 4 requires at least one Feishu user")
