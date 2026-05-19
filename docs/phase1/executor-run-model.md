# Phase 1 Executor Run Model

Phase 1 uses one Claude Code CLI session per task.

Flow:

```text
Task -> Executor Adapter -> new run_id -> Claude Code CLI -> logs/artifacts -> Task status update
```

Each run must bind:

- `project_id`
- `task_id`
- `run_id`
- `agent_role`
- `phase`
- `workspace_root`

The command working directory must be inside:

```text
workspaces/<project_id>/repo/
projects/<project_id>/
```

Long-running tmux/systemd/queue worker modes are Phase 4 concerns.
