from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted: bool
    reasons: list[str]


PATTERNS = [
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    ("api_key_assignment", re.compile(r"(?i)([A-Z0-9_]*API[_-]?KEY)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("password_assignment", re.compile(r"(?i)(password)\s*=\s*\S+"), r"\1=[REDACTED]"),
]


def redact_text(text: str) -> RedactionResult:
    redacted_text = text
    reasons: list[str] = []

    for reason, pattern, replacement in PATTERNS:
        redacted_text, count = pattern.subn(replacement, redacted_text)
        if count:
            reasons.append(reason)

    return RedactionResult(
        text=redacted_text,
        redacted=bool(reasons),
        reasons=reasons,
    )
