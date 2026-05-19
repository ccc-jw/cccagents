# Command Policy

Default automation boundary:

- L0: allow
- L1: allow when bound to a project
- L2: require approval
- L3: require approval

Deny:

- Cross-project workspace access
- Unbound write command
- Command containing visible API keys, tokens, or passwords
- L2/L3 command without approval

Classification examples:

| Command | Level | Decision |
| --- | --- | --- |
| `git status` | L0 | allow |
| `git diff` | L0 | allow |
| `pytest` | L1 | allow |
| `npm test` | L1 | allow |
| `npm install` | L2 | require approval |
| `pip install requests` | L2 | require approval |
| `git push` | L3 | require approval |
| `gh pr create` | L3 | require approval |
| `kubectl apply -f deploy.yaml` | L3 | require approval |
| `rm -rf /tmp/demo` | L3 | require approval |
