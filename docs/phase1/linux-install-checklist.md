# Phase 1A Linux Install Checklist

Target environment:

- Ubuntu 22.04 or 24.04
- Host installation, no Docker in Phase 1
- Normal Linux user for daily execution

Commands:

```bash
lsb_release -a
sudo apt update
sudo apt install -y curl git build-essential
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
sudo npm install -g @anthropic-ai/claude-code
claude --version
claude --help
```

Pass criteria:

- `claude --version` prints a version.
- `claude --help` prints help.
- Commands are saved in the Linux server operation log.
