from cccagents.redaction import redact_text


def test_redacts_bearer_tokens():
    text = "Authorization: Bearer abcdef1234567890"
    result = redact_text(text)

    assert result.text == "Authorization: Bearer [REDACTED]"
    assert result.redacted is True
    assert "bearer_token" in result.reasons


def test_redacts_api_key_assignments():
    text = "OPENAI_API_KEY=sk-test123456789"
    result = redact_text(text)

    assert result.text == "OPENAI_API_KEY=[REDACTED]"
    assert result.redacted is True
    assert "api_key_assignment" in result.reasons


def test_redacts_password_assignments():
    text = "password = supersecret"
    result = redact_text(text)

    assert result.text == "password=[REDACTED]"
    assert result.redacted is True
    assert "password_assignment" in result.reasons


def test_leaves_safe_text_unchanged():
    text = "npm test completed successfully"
    result = redact_text(text)

    assert result.text == text
    assert result.redacted is False
    assert result.reasons == []


def test_redacts_feishu_secret_assignments():
    text = "FEISHU_APP_SECRET=real-secret FEISHU_VERIFICATION_TOKEN=real-token FEISHU_ENCRYPT_KEY=real-key"
    result = redact_text(text)

    assert result.text == "FEISHU_APP_SECRET=[REDACTED] FEISHU_VERIFICATION_TOKEN=[REDACTED] FEISHU_ENCRYPT_KEY=[REDACTED]"
    assert result.redacted is True
    assert "secret_assignment" in result.reasons
    assert "token_assignment" in result.reasons


def test_redacts_lowercase_token_and_secret_assignments():
    text = "token=abc123 secret=xyz789 auth=BearerValue"
    result = redact_text(text)

    assert result.text == "token=[REDACTED] secret=[REDACTED] auth=[REDACTED]"
    assert result.redacted is True
    assert "token_assignment" in result.reasons
    assert "secret_assignment" in result.reasons
    assert "auth_assignment" in result.reasons
