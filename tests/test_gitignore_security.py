from pathlib import Path


def test_env_files_are_gitignored():
    content = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in content
    assert "*.env" in content
