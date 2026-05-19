import pytest

from cccagents.feishu_allowlist import FeishuAllowlist, validate_phase4_allowlist


def test_allows_known_feishu_user():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=False)

    decision = allowlist.decide("ou_123")

    assert decision.allowed is True
    assert decision.reason == "allowed_user"
    assert decision.redacted_user_id == "ou_***"


def test_denies_unknown_feishu_user():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=False)

    decision = allowlist.decide("ou_999")

    assert decision.allowed is False
    assert decision.reason == "user_not_allowlisted"
    assert decision.redacted_user_id == "ou_***"


def test_phase4_rejects_open_allow_all_users():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=True)

    with pytest.raises(ValueError, match="GATEWAY_ALLOW_ALL_USERS is not allowed in Phase 4"):
        validate_phase4_allowlist(allowlist)


def test_phase4_requires_at_least_one_user():
    allowlist = FeishuAllowlist(allowed_user_ids=set(), allow_all_users=False)

    with pytest.raises(ValueError, match="at least one Feishu user"):
        validate_phase4_allowlist(allowlist)
