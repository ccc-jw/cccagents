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
