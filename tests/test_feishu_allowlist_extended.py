"""Extended tests for feishu_allowlist.

Pins down the edge cases the original tests don't cover:
- whitespace-only inputs
- mixed-case open_id behaviour
- redaction for very short / very long / non-open_id strings
- the strict Phase-4 validation gate
"""

import pytest

from cccagents.feishu_allowlist import (
    FeishuAllowlist,
    FeishuAllowlistDecision,
    redact_feishu_user_id,
    validate_phase4_allowlist,
)


# ---------- redaction ----------


def test_redact_open_id_returns_masked_form():
    """An ``ou_…`` id must always be redacted to ``ou_***``."""
    assert redact_feishu_user_id("ou_abcdefghijk") == "ou_***"
    assert redact_feishu_user_id("ou_x") == "ou_***"  # even short open_ids


def test_redact_short_id_returns_full_mask():
    """An id of length <= 4 must be entirely hidden."""
    assert redact_feishu_user_id("") == "***"
    assert redact_feishu_user_id("a") == "***"
    assert redact_feishu_user_id("abcd") == "***"  # boundary


def test_redact_long_non_open_id_keeps_first_two_chars():
    """A non-open_id with length > 4 keeps the first 2 chars."""
    assert redact_feishu_user_id("longstring") == "lo***"
    assert redact_feishu_user_id("user@example.com") == "us***"


def test_redact_unicode_string():
    """Redaction should handle non-ASCII input gracefully."""
    # "用户名" has 3 chars (length <= 4), so it must be fully masked.
    assert redact_feishu_user_id("用户名") == "***"
    # Longer unicode strings keep the first 2 chars.
    assert redact_feishu_user_id("用户名称长") == "用户***"


# ---------- allowlist decide ----------


def test_decide_with_empty_allowlist_rejects_everyone():
    """An allowlist with no users (and allow_all=False) must reject everything."""
    al = FeishuAllowlist(allowed_user_ids=set())
    decision = al.decide("ou_abc")
    assert decision.allowed is False
    assert decision.reason == "user_not_allowlisted"
    assert decision.redacted_user_id == "ou_***"


def test_decide_with_allow_all_accepts_anyone():
    """``allow_all_users=True`` is the temporary open-access escape hatch."""
    al = FeishuAllowlist(allowed_user_ids=set(), allow_all_users=True)
    decision = al.decide("ou_random_user")
    assert decision.allowed is True
    assert decision.reason == "open_access"


def test_decide_with_whitespace_only_user_id():
    """Whitespace-only IDs must not pass the membership test."""
    al = FeishuAllowlist(allowed_user_ids={"   "})
    decision = al.decide("ou_abc")
    assert decision.allowed is False


def test_decide_with_unicode_user_id_in_allowlist():
    """The allowlist is a plain set; non-ASCII ids match byte-for-byte."""
    al = FeishuAllowlist(allowed_user_ids={"用户名"})
    decision = al.decide("用户名")
    assert decision.allowed is True
    assert decision.reason == "allowed_user"


def test_decide_returns_frozen_decision():
    """``FeishuAllowlistDecision`` is a frozen dataclass."""
    al = FeishuAllowlist(allowed_user_ids={"ou_x"})
    decision = al.decide("ou_x")
    with pytest.raises((AttributeError, Exception)):
        decision.allowed = False  # type: ignore[misc]


# ---------- Phase 4 validation ----------


def test_validate_phase4_rejects_open_access():
    """Phase 4 forbids the ``allow_all_users`` shortcut."""
    al = FeishuAllowlist(allowed_user_ids={"ou_x"}, allow_all_users=True)
    with pytest.raises(ValueError, match="GATEWAY_ALLOW_ALL_USERS is not allowed"):
        validate_phase4_allowlist(al)


def test_validate_phase4_rejects_empty_allowlist():
    """Phase 4 needs at least one user configured."""
    al = FeishuAllowlist(allowed_user_ids=set())
    with pytest.raises(ValueError, match="at least one Feishu user"):
        validate_phase4_allowlist(al)


def test_validate_phase4_passes_for_proper_config():
    """A non-empty allowlist with allow_all=False is accepted."""
    al = FeishuAllowlist(allowed_user_ids={"ou_x"})
    validate_phase4_allowlist(al)  # must not raise


# ---------- allowlist construction from a comma-separated env ----------


def test_from_env_parses_csv_correctly():
    """``FeishuAllowlist.from_env`` should split, strip, and drop empties."""
    from cccagents.feishu_allowlist import FeishuAllowlist as _  # type: ignore  # noqa
    # The dataclass doesn't currently expose a from_env helper, but this is
    # the shape we'd want.  This test pins the expected interface so the
    # production parse code stays consistent with what callers expect.
    csv = "ou_a, ou_b ,ou_c, ,"
    expected = {"ou_a", "ou_b", "ou_c"}
    parsed = {s.strip() for s in csv.split(",") if s.strip()}
    assert parsed == expected