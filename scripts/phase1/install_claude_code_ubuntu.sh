#!/usr/bin/env bash
set -euo pipefail

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
