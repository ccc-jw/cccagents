# cccagents Phase 2 Hermes 集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Linux 上验证实际 Hermes Agent 可承载 PM/PDM/RES/ARCH/DEV/TEST/SEC 角色，并能安全调用 Claude Code CLI 作为代码与文档执行器。

**Architecture:** Hermes 是 Agent 运行时、角色承载、记忆、Gateway 和任务协调入口；cccagents 只提供项目目录、审计、权限、脱敏和 Claude Code CLI executor 边界。Phase 2 先做无飞书的本地 Hermes 闭环，Phase 3 再启用 Feishu Gateway。

**Tech Stack:** NousResearch/hermes-agent、Claude Code CLI、Python 3.11+、SQLite/JSONL 项目日志、OpenAI-compatible model endpoint、Linux shell/systemd 后续预留。

---

## Task 1: 标记旧 Phase 2 方向已被 Hermes 集成方案取代

**Files:**
- Modify: `docs/superpowers/specs/2026-05-19-cccagents-phase2-workflow-design.md`
- Modify: `docs/superpowers/plans/2026-05-19-cccagents-phase2-workflow-plan.md`

- [ ] **Step 1: 在旧设计文档顶部加入 superseded 提示**

加入：

```markdown
> Superseded on 2026-05-19: 本文把角色设计成了本地 Python 工作流原型。根据用户确认，PM/PDM/RES/ARCH/DEV/TEST/SEC 必须运行在实际 Hermes 中。后续以 `docs/superpowers/specs/2026-05-19-cccagents-phase2-hermes-integration-design.md` 为准；本文仅作为流程规则和数据模型参考。
```

- [ ] **Step 2: 在旧计划文档顶部加入暂停提示**

加入：

```markdown
> Paused on 2026-05-19: 本计划 Task 8-10 不再继续执行，直到确认这些本地 Python 组件作为 Hermes 适配层仍然需要。新的 Phase 2 执行计划见 `docs/superpowers/plans/2026-05-19-cccagents-phase2-hermes-integration-plan.md`。
```

- [ ] **Step 3: 验证提示存在**

Run:

```bash
grep -n "Superseded on 2026-05-19\|Paused on 2026-05-19" docs/superpowers/specs/2026-05-19-cccagents-phase2-workflow-design.md docs/superpowers/plans/2026-05-19-cccagents-phase2-workflow-plan.md
```

Expected: 两个文件各输出一行匹配结果。

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-05-19-cccagents-phase2-workflow-design.md docs/superpowers/plans/2026-05-19-cccagents-phase2-workflow-plan.md
git commit -m "docs: mark local phase 2 workflow as superseded"
```

## Task 2: Linux 安装 Hermes Agent 并保存安装记录

**Files:**
- Create: `docs/phase2/linux-ops/hermes-install.log`
- Create: `docs/phase2/hermes-install-checklist.md`

- [ ] **Step 1: 创建 Linux 操作日志目录**

Run on Linux server repository copy:

```bash
mkdir -p docs/phase2/linux-ops
```

Expected: command exits 0.

- [ ] **Step 2: 写 Hermes 安装检查清单**

Create `docs/phase2/hermes-install-checklist.md`:

```markdown
# Phase 2 Hermes Install Checklist

Date: 2026-05-19

## Goal

Install NousResearch Hermes Agent on Linux and verify the `hermes` CLI is available.

## Commands

```bash
python3 --version
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes --help
hermes doctor
```

## Evidence

Save command output to:

```text
docs/phase2/linux-ops/hermes-install.log
```

## Secret Rule

Do not write real API keys, Feishu secrets, or tokens into this file or the operation log.
```
```

- [ ] **Step 3: 执行安装并记录输出**

Run on Linux server:

```bash
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  python3 --version
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  source ~/.bashrc
  hermes --help
  hermes doctor
} 2>&1 | tee docs/phase2/linux-ops/hermes-install.log
```

Expected: `hermes --help` prints CLI help; `hermes doctor` either passes or reports concrete missing configuration.

- [ ] **Step 4: 检查日志没有密钥**

Run:

```bash
grep -Ei "api[_-]?key|secret|token|password" docs/phase2/linux-ops/hermes-install.log || true
```

Expected: no real secret values. If config variable names appear, confirm no credential value appears.

- [ ] **Step 5: Commit**

```bash
git add docs/phase2/hermes-install-checklist.md docs/phase2/linux-ops/hermes-install.log
git commit -m "docs: record hermes linux installation"
```

## Task 3: 采集 Hermes 配置、模型、工具和 Gateway 能力

**Files:**
- Create: `scripts/phase2/collect_hermes_capabilities.sh`
- Create: `docs/phase2/hermes-capability-report.md`
- Create: `docs/phase2/linux-ops/hermes-capability-collection.log`

- [ ] **Step 1: 写采集脚本**

Create `scripts/phase2/collect_hermes_capabilities.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-docs/phase2/hermes-capability-report.md}"
mkdir -p "$(dirname "$OUTPUT")"

{
  printf '# Phase 2 Hermes Capability Report\n\n'
  printf 'Generated at: %s\n\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  printf '## hermes version/help\n\n```text\n'
  hermes --help || true
  printf '\n```\n\n'

  printf '## hermes doctor\n\n```text\n'
  hermes doctor || true
  printf '\n```\n\n'

  printf '## hermes model\n\n```text\n'
  hermes model --help || hermes model || true
  printf '\n```\n\n'

  printf '## hermes tools\n\n```text\n'
  hermes tools --help || hermes tools || true
  printf '\n```\n\n'

  printf '## hermes gateway\n\n```text\n'
  hermes gateway --help || true
  printf '\n```\n\n'

  printf '## config files\n\n```text\n'
  ls -la ~/.hermes || true
  printf '\n```\n'
} > "$OUTPUT"
```

- [ ] **Step 2: 运行采集脚本**

Run:

```bash
chmod +x scripts/phase2/collect_hermes_capabilities.sh
scripts/phase2/collect_hermes_capabilities.sh docs/phase2/hermes-capability-report.md 2>&1 | tee docs/phase2/linux-ops/hermes-capability-collection.log
```

Expected: report file created.

- [ ] **Step 3: 验证关键能力记录存在**

Run:

```bash
grep -n "hermes doctor\|hermes model\|hermes tools\|hermes gateway\|config files" docs/phase2/hermes-capability-report.md
```

Expected: all section headings found.

- [ ] **Step 4: Commit**

```bash
git add scripts/phase2/collect_hermes_capabilities.sh docs/phase2/hermes-capability-report.md docs/phase2/linux-ops/hermes-capability-collection.log
git commit -m "docs: collect hermes capability evidence"
```

## Task 4: 配置并验证 Hermes OpenAI 兼容模型

**Files:**
- Create: `docs/phase2/hermes-openai-compat-gate.md`
- Create: `docs/phase2/linux-ops/hermes-openai-compat.log`

- [ ] **Step 1: 写模型门禁文档**

Create `docs/phase2/hermes-openai-compat-gate.md`:

```markdown
# Phase 2 Hermes OpenAI Compatibility Gate

Date: 2026-05-19

## Gate

Hermes itself must be able to use the user's OpenAI-compatible model endpoint. Claude Code CLI support alone is not sufficient for Phase 2 pass.

## Required configuration shape

Hermes stores non-secret settings in:

```text
~/.hermes/config.yaml
```

Hermes stores secrets in:

```text
~/.hermes/.env
```

The user endpoint must be represented without writing the real API key into project files.

## Verification command

Use Hermes CLI or one-shot mode to ask for a deterministic reply:

```text
只回复 OK
```

Expected output:

```text
OK
```

## Evidence

Save redacted output to:

```text
docs/phase2/linux-ops/hermes-openai-compat.log
```
```

- [ ] **Step 2: 配置 Hermes 模型**

Run interactively or by editing `~/.hermes/config.yaml` and `~/.hermes/.env` on Linux. Use the user gateway values, but never paste the real API key into repository files.

Expected config intent:

```yaml
model:
  provider: custom
  model: qwen3.6-plus
  base_url: http://cccai.store/v1
```

Hermes 的 `model.base_url` 必须包含 OpenAI-compatible API 路径 `/v1`。已验证 `http://cccai.store` 会导致 Hermes 建连但 `hermes chat` 空响应；`http://cccai.store/v1` 可返回 `OK`。

Expected secret location:

```text
~/.hermes/.env contains the API key or secret reference only on the Linux host.
```

- [ ] **Step 3: 验证 Hermes 最小对话**

Run a Hermes CLI command supported by the installed version, for example one-shot or interactive prompt, and save redacted output:

```bash
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  hermes -p "只回复 OK" || hermes --help
} 2>&1 | sed -E 's/(api[_-]?key|authorization|bearer)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig' | tee docs/phase2/linux-ops/hermes-openai-compat.log
```

Expected: output contains `OK`. If `hermes -p` is unsupported, document the supported command discovered from `hermes --help` and rerun.

- [ ] **Step 4: Commit**

```bash
git add docs/phase2/hermes-openai-compat-gate.md docs/phase2/linux-ops/hermes-openai-compat.log
git commit -m "docs: verify hermes openai compatible model gate"
```

## Task 5: 定义 Hermes 角色技能草案

**Files:**
- Create: `hermes/roles/pm.md`
- Create: `hermes/roles/pdm.md`
- Create: `hermes/roles/res.md`
- Create: `hermes/roles/arch.md`
- Create: `hermes/roles/dev.md`
- Create: `hermes/roles/test.md`
- Create: `hermes/roles/sec.md`
- Create: `tests/test_hermes_roles.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_hermes_roles.py`:

```python
from pathlib import Path


ROLES = {
    "pm.md": ["项目经理", "task router", "review gate"],
    "pdm.md": ["产品经理", "PRD", "acceptance"],
    "res.md": ["调研员", "research", "feasibility"],
    "arch.md": ["架构师", "tech-design", "ARCH/DEV 与 TEST"],
    "dev.md": ["开发工程师", "Claude Code CLI", "self-test"],
    "test.md": ["测试工程师", "test-checklist", "Excel"],
    "sec.md": ["安全工程师", "security", "SAST"],
}


def test_hermes_role_files_define_required_contracts():
    role_dir = Path("hermes/roles")

    for filename, required_terms in ROLES.items():
        content = (role_dir / filename).read_text(encoding="utf-8")
        assert "## Role" in content
        assert "## Inputs" in content
        assert "## Outputs" in content
        assert "## Forbidden" in content
        assert "## Tool Access" in content
        for term in required_terms:
            assert term in content
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
. .venv/bin/activate
pytest tests/test_hermes_roles.py -v
```

Expected: FAIL because role files do not exist.

- [ ] **Step 3: 写角色文件**

Create the seven role files with this structure.

`hermes/roles/pm.md`:

```markdown
# PM Agent Role

## Role

项目经理。User-facing coordinator inside Hermes. Owns project state, task router, review gate, risk summary, and user interruption policy.

## Inputs

- User project goal
- Project state
- Task state
- Review results
- Issue lists
- Command and Hermes run logs

## Outputs

- Next phase decision
- Next handler role
- Review gate summary
- User-facing progress or risk summary

## Forbidden

- Do not implement code directly unless explicitly acting as DEV.
- Do not expose API keys or secrets.
- Do not let ARCH/DEV and TEST exchange draft artifacts during the isolation period.

## Tool Access

- Hermes memory
- Hermes subagent
- Hermes skills
- Read-only project state tools
- Claude Code CLI only for progress reports and summaries
```

`hermes/roles/pdm.md`:

```markdown
# PDM Agent Role

## Role

产品经理。Owns requirement clarification, PRD drafting, PRD revision, requirement review fixes, and product acceptance.

## Inputs

- User requirement conversation
- Requirement review issues
- Clarification questions from ARCH, DEV, TEST, SEC, RES
- Test and security validation reports

## Outputs

- PRD draft
- PRD final
- clarification-log.md
- acceptance-report.md
- acceptance-issues.md

## Forbidden

- Do not decide technical implementation details for ARCH/DEV.
- Do not hide requirement changes from PM.
- Do not expose secrets.

## Tool Access

- Hermes memory
- Hermes skills
- Claude Code CLI for PRD and acceptance document generation
```

`hermes/roles/res.md`:

```markdown
# RES Agent Role

## Role

调研员。Produces research, feasibility analysis, current-state investigation, and alternatives for product and architecture decisions.

## Inputs

- Research topic
- PRD draft or final
- Existing code or documentation references

## Outputs

- research-report.<topic>.md
- feasibility conclusion
- risks and alternatives

## Forbidden

- Do not change workflow phase directly.
- Do not implement production code.
- Do not expose secrets.

## Tool Access

- Hermes memory
- Hermes skills
- Read-only terminal commands
- Claude Code CLI for research report generation
```

`hermes/roles/arch.md`:

```markdown
# ARCH Agent Role

## Role

架构师。Owns tech-design, API design, database design, module boundaries, development breakdown, and technical risk handling.

## Inputs

- PRD final
- clarification-log.md
- research reports
- Existing codebase state

## Outputs

- tech-design.draft.md
- tech-design.final.md
- api-design.md
- database-design.md
- dev-breakdown.md
- tech-design-review.md

## Forbidden

- During draft isolation, ARCH/DEV 与 TEST must not exchange draft artifacts or direct clarifications.
- Do not start coding before tech-design and test-case gates both pass.
- Do not expose secrets.

## Tool Access

- Hermes memory
- Hermes skills
- Read-only terminal commands
- Claude Code CLI for architecture documents and codebase analysis
```

`hermes/roles/dev.md`:

```markdown
# DEV Agent Role

## Role

开发工程师。Implements code, updates design notes when needed, runs self-test, integration test, smoke test, and fixes defects from TEST, SEC, and PDM.

## Inputs

- PRD final
- tech-design.final.md
- test-cases.final.md
- defect-log.md
- security-issues.md
- acceptance-issues.md

## Outputs

- Source code changes
- dev-notes.md
- self-test-report.md
- integration-test-report.md
- smoke-test-report.md
- fix notes

## Forbidden

- Do not run L2/L3 commands without PM approval.
- Do not write outside the project workspace or project artifact directory.
- Do not expose secrets.

## Tool Access

- Hermes terminal
- Hermes skills
- Claude Code CLI for coding, tests, documentation, and fixes
```

`hermes/roles/test.md`:

```markdown
# TEST Agent Role

## Role

测试工程师。Owns test cases, Markdown test-checklist, Excel checklist, test execution, defect logging, and regression verification.

## Inputs

- PRD final
- clarification-log.md
- Runnable code
- DEV self-test and smoke reports

## Outputs

- test-cases.draft.md
- test-cases.final.md
- test-checklist.draft.md
- test-checklist.final.md
- test-checklist.draft.xlsx
- test-checklist.final.xlsx
- test-execution-report.md
- defect-log.md
- regression-report.md

## Forbidden

- During draft isolation, do not communicate with ARCH/DEV or read their unapproved draft.
- Do not change source code directly.
- Do not expose secrets.

## Tool Access

- Hermes terminal
- Hermes skills
- Claude Code CLI for test documents, test execution, and Excel checklist generation
```

`hermes/roles/sec.md`:

```markdown
# SEC Agent Role

## Role

安全工程师。Owns security review, SAST-style checks, dependency/config/log/secret review, security issue logging, and security regression verification.

## Inputs

- PRD final
- tech-design.final.md
- Runnable code
- Dependency files
- Configuration files

## Outputs

- security-review.md
- security-issues.md
- security-regression-report.md

## Forbidden

- Do not exploit external systems.
- Do not run destructive security tests or DoS.
- Do not expose secrets.

## Tool Access

- Hermes terminal
- Hermes skills
- Claude Code CLI for security review, local static checks, and report generation
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
. .venv/bin/activate
pytest tests/test_hermes_roles.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add hermes/roles tests/test_hermes_roles.py
git commit -m "feat: define hermes software team roles"
```

## Task 6: 实现 Claude Code CLI executor wrapper

**Files:**
- Create: `src/cccagents/claude_executor.py`
- Create: `tests/test_claude_executor.py`

- [ ] **Step 1: 写失败测试**

Create `tests/test_claude_executor.py`:

```python
from pathlib import Path

import pytest

from cccagents.claude_executor import build_claude_command
from cccagents.phase2_models import AgentModelConfig


def test_build_claude_command_uses_prompt_model_and_text_output():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="qwen3.6-plus",
    )

    command = build_claude_command(config, "只回复 OK")

    assert command == [
        "claude",
        "-p",
        "只回复 OK",
        "--model",
        "qwen3.6-plus",
        "--output-format",
        "text",
    ]


def test_build_claude_command_rejects_empty_prompt():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="qwen3.6-plus",
    )

    with pytest.raises(ValueError, match="prompt is required"):
        build_claude_command(config, "")
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
. .venv/bin/activate
pytest tests/test_claude_executor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.claude_executor'`.

- [ ] **Step 3: 写最小实现**

Create `src/cccagents/claude_executor.py`:

```python
from cccagents.phase2_models import AgentModelConfig


def build_claude_command(config: AgentModelConfig, prompt: str) -> list[str]:
    if not prompt:
        raise ValueError("prompt is required")
    return [
        "claude",
        "-p",
        prompt,
        "--model",
        config.model_name,
        "--output-format",
        "text",
    ]
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
. .venv/bin/activate
pytest tests/test_claude_executor.py tests/test_agent_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/claude_executor.py tests/test_claude_executor.py
git commit -m "feat: add claude code executor command builder"
```

## Task 7: 定义 Hermes 到 Claude executor 的最小任务协议

**Files:**
- Create: `docs/phase2/hermes-claude-executor-protocol.md`
- Create: `tests/test_executor_protocol_doc.py`

- [ ] **Step 1: 写文档测试**

Create `tests/test_executor_protocol_doc.py`:

```python
from pathlib import Path


def test_executor_protocol_documents_required_fields_and_security_rules():
    content = Path("docs/phase2/hermes-claude-executor-protocol.md").read_text(encoding="utf-8")

    for required in [
        "project_id",
        "task_id",
        "run_id",
        "agent_role",
        "phase",
        "cwd",
        "prompt",
        "allowed_tools",
        "permission_mode",
        "env_refs",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "command-log.jsonl",
        "真实 API Key 不得写入",
    ]:
        assert required in content
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
. .venv/bin/activate
pytest tests/test_executor_protocol_doc.py -v
```

Expected: FAIL because document does not exist.

- [ ] **Step 3: 写协议文档**

Create `docs/phase2/hermes-claude-executor-protocol.md`:

```markdown
# Hermes to Claude Code CLI Executor Protocol

Date: 2026-05-19

## Request

```text
project_id
task_id
run_id
agent_role
phase
cwd
prompt
allowed_tools
permission_mode
env_refs
```

## Environment Mapping

```text
model_base_url -> ANTHROPIC_BASE_URL
resolved model_api_key_ref -> ANTHROPIC_API_KEY
model_name -> ANTHROPIC_MODEL
```

## Command

```bash
claude -p "$PROMPT" --model "$ANTHROPIC_MODEL" --output-format text
```

## Path Rule

`cwd` must be inside one of:

```text
workspaces/<project_id>/repo/
projects/<project_id>/
```

## Audit Rule

Each execution writes a record to:

```text
projects/<project_id>/08-logs/command-log.jsonl
```

and detailed run files to:

```text
projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

## Secret Rule

真实 API Key 不得写入 repository files, project artifacts, command-log.jsonl, Hermes prompts, Feishu messages, stdout logs, or stderr logs. Store only `model_api_key_ref` and redacted evidence.
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
. .venv/bin/activate
pytest tests/test_executor_protocol_doc.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/phase2/hermes-claude-executor-protocol.md tests/test_executor_protocol_doc.py
git commit -m "docs: define hermes claude executor protocol"
```

## Task 8: 跑通无飞书 Hermes 最小闭环

**Files:**
- Create: `docs/phase2/linux-ops/hermes-local-loop.log`
- Create: `docs/phase2/hermes-local-loop-report.md`

- [ ] **Step 1: 初始化项目目录**

Run on Linux:

```bash
python - <<'PY'
from pathlib import Path
from cccagents.paths import ProjectPaths
from cccagents.project_init import initialize_project_structure

paths = ProjectPaths(root=Path.home() / "cccagents", project_id="phase2-hermes-smoke")
for path in initialize_project_structure(paths):
    print(path)
PY
```

Expected: project and workspace directories printed.

- [ ] **Step 2: 让 Hermes PM 模拟派发 DEV 任务**

Use the installed Hermes command discovered in Task 3. The prompt must say:

```text
你是 cccagents 的 PM Agent。请模拟把一个最小 DEV 任务派发给 DEV：在 project_id=phase2-hermes-smoke 的项目目录中，通过 Claude Code CLI 生成一个 hello-from-dev.txt 文件。只输出你要派发给 DEV 的任务说明，不要执行。
```

Save output to `docs/phase2/linux-ops/hermes-local-loop.log`.

Expected: Hermes returns a DEV task prompt.

- [ ] **Step 3: 执行 DEV 的 Claude Code CLI 动作**

Run the Claude Code CLI executor command in the project workspace with redacted env evidence:

```bash
cd "$HOME/cccagents/workspaces/phase2-hermes-smoke/repo"
ANTHROPIC_BASE_URL="http://cccai.store" \
ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
ANTHROPIC_MODEL="qwen3.6-plus" \
claude -p "Create a file named hello-from-dev.txt containing exactly: hello from DEV" --model qwen3.6-plus --output-format text
```

Expected: file exists and contains `hello from DEV`.

- [ ] **Step 4: 写闭环报告**

Create `docs/phase2/hermes-local-loop-report.md`:

```markdown
# Phase 2 Hermes Local Loop Report

Date: 2026-05-19

## Scenario

Local no-Feishu loop: user goal -> Hermes PM simulation -> DEV task -> Claude Code CLI executor -> project artifact.

## Result

- Hermes PM task generation: pass/fail
- Claude Code CLI executor: pass/fail
- Project file created: pass/fail

## Evidence

- `docs/phase2/linux-ops/hermes-local-loop.log`
- `workspaces/phase2-hermes-smoke/repo/hello-from-dev.txt`

## Secret Check

No real API key is stored in project files or logs.
```

Fill pass/fail based on actual result.

- [ ] **Step 5: Commit**

```bash
git add docs/phase2/linux-ops/hermes-local-loop.log docs/phase2/hermes-local-loop-report.md
git commit -m "docs: verify hermes local role execution loop"
```

## Task 9: Phase 2 总体验收

**Files:**
- Create: `docs/phase2/phase2-acceptance.md`

- [ ] **Step 1: 写验收报告**

Create `docs/phase2/phase2-acceptance.md`:

```markdown
# Phase 2 Acceptance

Date: 2026-05-19

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes installed on Linux | pass/fail | docs/phase2/linux-ops/hermes-install.log |
| Hermes doctor has no blocking issue | pass/fail | docs/phase2/hermes-capability-report.md |
| Hermes OpenAI-compatible model works | pass/fail | docs/phase2/linux-ops/hermes-openai-compat.log |
| Hermes role definitions exist | pass/fail | hermes/roles/ |
| Hermes can route a minimal PM -> DEV task | pass/fail | docs/phase2/linux-ops/hermes-local-loop.log |
| Claude Code CLI executor works under Hermes flow | pass/fail | docs/phase2/hermes-local-loop-report.md |
| Project artifacts are project_id isolated | pass/fail | projects/phase2-hermes-smoke/ |
| No real API key in committed evidence | pass/fail | grep verification |

## Decision

Proceed to Phase 3 Feishu integration only if all blocking gates pass.

## Open Issues

- None, or list exact blocker with owner and next action.
```

- [ ] **Step 2: 运行本地测试**

Run:

```bash
. .venv/bin/activate
pytest -v
```

Expected: PASS.

- [ ] **Step 3: 检查密钥泄漏**

Run:

```bash
grep -R "sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

Expected: no real API key values.

- [ ] **Step 4: Commit**

```bash
git add docs/phase2/phase2-acceptance.md
git commit -m "docs: add phase 2 hermes acceptance report"
```
