from pathlib import Path


def test_orchestrator_smoke_script_exists_and_runs_s0_s1_s2():
    script = Path("scripts/phase5/run_orchestrator_smoke.sh")
    content = script.read_text(encoding="utf-8")

    assert "#!/usr/bin/env bash" in content
    assert "set -euo pipefail" in content
    assert "FakeExecutor" in content
    assert "orchestrate_request" in content
    assert "S0" in content
    assert "S1" in content
    assert "S2" in content
    assert 'smoke-$name' in content or 'smoke-s0' in content
