import shlex


L3_PREFIXES = (
    ("git", "push"),
    ("gh", "pr", "create"),
    ("kubectl",),
    ("terraform", "apply"),
    ("rm",),
)

L2_PREFIXES = (
    ("npm", "install"),
    ("pip", "install"),
    ("alembic", "upgrade"),
    ("npm", "run", "migrate"),
)

L1_PREFIXES = (
    ("pytest",),
    ("npm", "test"),
    ("mkdir",),
    ("python",),
)

L0_PREFIXES = (
    ("ls",),
    ("git", "status"),
    ("git", "diff"),
    ("rg",),
    ("grep",),
)


def _starts_with(parts: list[str], prefix: tuple[str, ...]) -> bool:
    return len(parts) >= len(prefix) and tuple(parts[: len(prefix)]) == prefix


def classify_command(command: str) -> str:
    parts = shlex.split(command)
    if not parts:
        return "L0"

    if "--force" in parts or "-rf" in parts or "-fr" in parts:
        return "L3"

    for prefix in L3_PREFIXES:
        if _starts_with(parts, prefix):
            return "L3"

    for prefix in L2_PREFIXES:
        if _starts_with(parts, prefix):
            return "L2"

    for prefix in L1_PREFIXES:
        if _starts_with(parts, prefix):
            return "L1"

    for prefix in L0_PREFIXES:
        if _starts_with(parts, prefix):
            return "L0"

    return "L2"


def decide_command(permission_level: str, bound_project: bool = True) -> str:
    if permission_level in {"L1", "L2", "L3"} and not bound_project:
        return "deny"
    if permission_level in {"L0", "L1"}:
        return "allow"
    if permission_level in {"L2", "L3"}:
        return "require_approval"
    return "deny"
