# Phase 2 Hermes Capability Report

Generated at: 2026-05-19T13:06:28Z

## hermes version/help

```text
usage: hermes [-h] [--version] [-z PROMPT] [-m MODEL] [--provider PROVIDER]
              [-t TOOLSETS] [--resume SESSION] [--continue [SESSION_NAME]]
              [--worktree] [--accept-hooks] [--skills SKILLS] [--yolo]
              [--pass-session-id] [--ignore-user-config] [--ignore-rules]
              [--tui] [--dev]
              {chat,model,fallback,gateway,proxy,lsp,setup,postinstall,whatsapp,slack,send,login,logout,auth,status,cron,webhook,kanban,hooks,doctor,dump,debug,backup,checkpoints,import,config,pairing,skills,bundles,plugins,curator,memory,tools,computer-use,mcp,sessions,insights,claw,version,update,uninstall,acp,profile,completion,dashboard,logs}
              ...

Hermes Agent - AI assistant with tool-calling capabilities

positional arguments:
  {chat,model,fallback,gateway,proxy,lsp,setup,postinstall,whatsapp,slack,send,login,logout,auth,status,cron,webhook,kanban,hooks,doctor,dump,debug,backup,checkpoints,import,config,pairing,skills,bundles,plugins,curator,memory,tools,computer-use,mcp,sessions,insights,claw,version,update,uninstall,acp,profile,completion,dashboard,logs}
                        Command to run
    chat                Interactive chat with the agent
    model               Select default model and provider
    fallback            Manage fallback providers (tried when the primary
                        model fails)
    gateway             Messaging gateway management
    proxy               Local OpenAI-compatible proxy to OAuth providers
    lsp                 Language Server Protocol management
    setup               Interactive setup wizard
    postinstall         Bootstrap non-Python deps for pip installs (node,
                        browser, ripgrep, ffmpeg)
    whatsapp            Set up WhatsApp integration
    slack               Slack integration helpers (manifest generation, etc.)
    send                Send a message to a configured platform (scripts, cron
                        jobs, CI).
    login               Authenticate with an inference provider
    logout              Clear authentication for an inference provider
    auth                Manage pooled provider credentials
    status              Show status of all components
    cron                Cron job management
    webhook             Manage dynamic webhook subscriptions
    kanban              Multi-profile collaboration board (tasks, links,
                        comments)
    hooks               Inspect and manage shell-script hooks
    doctor              Check configuration and dependencies
    dump                Dump setup summary for support/debugging
    debug               Debug tools — upload logs and system info for support
    backup              Back up Hermes home directory to a zip file
    checkpoints         Inspect / prune / clear ~/.hermes/checkpoints/
    import              Restore a Hermes backup from a zip file
    config              View and edit configuration
    pairing             Manage DM pairing codes for user authorization
    skills              Search, install, configure, and manage skills
    bundles             Create, list, and manage skill bundles (aliases for
                        multiple skills)
    plugins             Manage plugins — install, update, remove, list
    curator             Background skill maintenance (curator) — status, run,
                        pause, pin
    memory              Configure external memory provider
    tools               Configure which tools are enabled per platform
    computer-use        Manage the Computer Use (cua-driver) backend (macOS)
    mcp                 Manage MCP servers and run Hermes as an MCP server
    sessions            Manage session history (list, rename, export, prune,
                        delete)
    insights            Show usage insights and analytics
    claw                OpenClaw migration tools
    version             Show version information
    update              Update Hermes Agent to the latest version
    uninstall           Uninstall Hermes Agent
    acp                 Run Hermes Agent as an ACP (Agent Client Protocol)
                        server
    profile             Manage profiles — multiple isolated Hermes instances
    completion          Print shell completion script (bash, zsh, or fish)
    dashboard           Start the web UI dashboard
    logs                View and filter Hermes log files

options:
  -h, --help            show this help message and exit
  --version, -V         Show version and exit
  -z PROMPT, --oneshot PROMPT
                        One-shot mode: send a single prompt and print ONLY the
                        final response text to stdout. No banner, no spinner,
                        no tool previews, no session_id line. Tools, memory,
                        rules, and AGENTS.md in the CWD are loaded as normal;
                        approvals are auto-bypassed. Intended for scripts /
                        pipes.
  -m MODEL, --model MODEL
                        Model override for this invocation (e.g.
                        anthropic/claude-sonnet-4.6). Applies to -z/--oneshot
                        and --tui. Also settable via HERMES_INFERENCE_MODEL
                        env var.
  --provider PROVIDER   Provider override for this invocation (e.g.
                        openrouter, anthropic). Applies to -z/--oneshot and
                        --tui. Also settable via HERMES_INFERENCE_PROVIDER env
                        var.
  -t TOOLSETS, --toolsets TOOLSETS
                        Comma-separated toolsets to enable for this
                        invocation. Applies to -z/--oneshot and --tui.
  --resume SESSION, -r SESSION
                        Resume a previous session by ID or title
  --continue [SESSION_NAME], -c [SESSION_NAME]
                        Resume a session by name, or the most recent if no
                        name given
  --worktree, -w        Run in an isolated git worktree (for parallel agents)
  --accept-hooks        Auto-approve any unseen shell hooks declared in
                        config.yaml without a TTY prompt. Equivalent to
                        HERMES_ACCEPT_HOOKS=1 or hooks_auto_accept: true in
                        config.yaml. Use on CI / headless runs that can't
                        prompt.
  --skills SKILLS, -s SKILLS
                        Preload one or more skills for the session (repeat
                        flag or comma-separate)
  --yolo                Bypass all dangerous command approval prompts (use at
                        your own risk)
  --pass-session-id     Include the session ID in the agent's system prompt
  --ignore-user-config  Ignore ~/.hermes/config.yaml and fall back to built-in
                        defaults (credentials in .env are still loaded)
  --ignore-rules        Skip auto-injection of AGENTS.md, SOUL.md,
                        .cursorrules, memory, and preloaded skills
  --tui                 Launch the modern TUI instead of the classic REPL
  --dev                 With --tui: run TypeScript sources via tsx (skip dist
                        build)

Examples:
    hermes                        Start interactive chat
    hermes chat -q "Hello"        Single query mode
    hermes -c                     Resume the most recent session
    hermes -c "my project"        Resume a session by name (latest in lineage)
    hermes --resume <session_id>  Resume a specific session by ID
    hermes setup                  Run setup wizard
    hermes logout                 Clear stored authentication
    hermes auth add <provider>    Add a pooled credential
    hermes auth list              List pooled credentials
    hermes auth remove <p> <t>    Remove pooled credential by index, id, or label
    hermes auth reset <provider>  Clear exhaustion status for a provider
    hermes model                  Select default model
    hermes fallback [list]        Show fallback provider chain
    hermes fallback add           Add a fallback provider (same picker as `hermes model`)
    hermes fallback remove        Remove a fallback provider from the chain
    hermes config                 View configuration
    hermes config edit            Edit config in $EDITOR
    hermes config set model gpt-4 Set a config value
    hermes gateway                Run messaging gateway
    hermes -s hermes-agent-dev,github-auth
    hermes -w                     Start in isolated git worktree
    hermes gateway install        Install gateway background service
    hermes sessions list          List past sessions
    hermes sessions browse        Interactive session picker
    hermes sessions rename ID T   Rename/title a session
    hermes logs                   View agent.log (last 50 lines)
    hermes logs -f                Follow agent.log in real time
    hermes logs errors            View errors.log
    hermes logs --since 1h        Lines from the last hour
    hermes debug share             Upload debug report for support
    hermes update                 Update to latest version
    hermes dashboard              Start web UI dashboard (port 9119)
    hermes dashboard --stop       Stop running dashboard processes
    hermes dashboard --status     List running dashboard processes

For more help on a command:
    hermes <command> --help

```

## hermes doctor

```text

┌─────────────────────────────────────────────────────────┐
│                 🩺 Hermes Doctor                        │
└─────────────────────────────────────────────────────────┘

◆ Security Advisories
  ✓ No active security advisories

◆ Python Environment
  ✓ Python 3.11.15
  ✓ Virtual environment active

◆ Required Packages
  ✓ OpenAI SDK
  ✓ Rich (terminal UI)
  ✓ python-dotenv
  ✓ PyYAML
  ✓ HTTPX
  ✓ Croniter (cron expressions) (optional)
  ⚠ python-telegram-bot (optional, not installed)
  ⚠ discord.py (optional, not installed)

◆ Configuration Files
  ✓ ~/.hermes/.env file exists
  ✓ API key or custom endpoint configured
  ✓ ~/.hermes/config.yaml exists
  ✓ Config version up to date (v23)

◆ Auth Providers
  ⚠ Nous Portal auth (not logged in)
  ⚠ OpenAI Codex auth (not logged in)
    → No Codex credentials stored. Run `hermes auth` to authenticate.
    → codex CLI not installed (optional — only required to import tokens from an existing Codex CLI login)
  ⚠ Google Gemini OAuth (not logged in)
  ⚠ MiniMax OAuth (not logged in)
  ⚠ xAI OAuth (not logged in)
    → No xAI OAuth credentials stored. Select xAI Grok OAuth (SuperGrok Subscription) in `hermes model`.

◆ Directory Structure
  ✓ ~/.hermes directory exists
  ✓ ~/.hermes/cron/ exists
  ✓ ~/.hermes/sessions/ exists
  ✓ ~/.hermes/logs/ exists
  ✓ ~/.hermes/skills/ exists
  ✓ ~/.hermes/memories/ exists
  ✓ ~/.hermes/SOUL.md exists (persona configured)
  ✓ ~/.hermes/memories/ directory exists
    → MEMORY.md not created yet (will be created when the agent first writes a memory)
    → USER.md not created yet (will be created when the agent first writes a memory)
    → ~/.hermes/state.db not created yet (will be created on first session)

◆ Command Installation
  ✓ Venv entry point exists (venv/bin/hermes)
  ✓ ~/.local/bin/hermes exists (non-symlink)

◆ External Tools
  ✓ git
  ✓ ripgrep (rg) (faster file search)
  ⚠ docker not found (optional)
  ✓ Node.js
  ✓ agent-browser (Node.js) (browser automation)
  ✓ Playwright Chromium (browser engine)
  ✓ Browser tools (agent-browser) deps (no known vulnerabilities)

◆ API Connectivity
  Running 27 connectivity checks in parallel…                                                                        ⚠ OpenRouter API (not configured)

◆ Tool Availability
  ✓ browser
  ✓ clarify
  ✓ code_execution
  ✓ cronjob
  ✓ terminal
  ✓ delegation
  ✓ file
  ✓ memory
  ✓ session_search
  ✓ skills
  ✓ todo
  ✓ tts
  ✓ kanban (runtime-gated; loaded only for dispatcher-spawned workers)
  ⚠ browser-cdp (system dependency not met)
  ⚠ computer_use (system dependency not met)
  ⚠ discord (missing DISCORD_BOT_TOKEN)
  ⚠ discord_admin (missing DISCORD_BOT_TOKEN)
  ⚠ feishu_doc (system dependency not met)
  ⚠ feishu_drive (system dependency not met)
  ⚠ homeassistant (system dependency not met)
  ⚠ image_gen (system dependency not met)
  ⚠ moa (missing OPENROUTER_API_KEY)
  ⚠ messaging (system dependency not met)
  ⚠ video_gen (system dependency not met)
  ⚠ vision (system dependency not met)
  ⚠ video (system dependency not met)
  ⚠ web (missing EXA_API_KEY, PARALLEL_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY, FIRECRAWL_API_URL, FIRECRAWL_GATEWAY_URL, TOOL_GATEWAY_DOMAIN, TOOL_GATEWAY_SCHEME, TOOL_GATEWAY_USER_TOKEN)
  ⚠ x_search (missing XAI_API_KEY)
  ⚠ hermes-yuanbao (system dependency not met)
  ⚠ spotify (system dependency not met)

◆ Skills Hub
  ⚠ Skills Hub directory not initialized (run: hermes skills list)
  ⚠ No GITHUB_TOKEN (60 req/hr rate limit — set in ~/.hermes/.env for better rates)

◆ Memory Provider
  ✓ Built-in memory active (no external provider configured — this is fine)

────────────────────────────────────────────────────────────
  Found 1 issue(s) to address:

  1. Run 'hermes setup' to configure missing API keys for full tool access

  Tip: run 'hermes doctor --fix' to auto-fix what's possible.


```

## hermes model

```text
usage: hermes model [-h] [--portal-url PORTAL_URL]
                    [--inference-url INFERENCE_URL] [--client-id CLIENT_ID]
                    [--scope SCOPE] [--no-browser] [--manual-paste]
                    [--timeout TIMEOUT] [--ca-bundle CA_BUNDLE] [--insecure]

Interactively select your inference provider and default model

options:
  -h, --help            show this help message and exit
  --portal-url PORTAL_URL
                        Portal base URL for Nous login (default: production
                        portal)
  --inference-url INFERENCE_URL
                        Inference API base URL for Nous login (default:
                        production inference API)
  --client-id CLIENT_ID
                        OAuth client id to use for Nous login (default:
                        hermes-cli)
  --scope SCOPE         OAuth scope to request for Nous login
  --no-browser          Do not attempt to open the browser automatically
                        during Nous login
  --manual-paste        For loopback OAuth providers (xai-oauth, ...): skip
                        the local callback listener and paste the failed
                        callback URL from your browser instead. Use on
                        browser-only remotes (Cloud Shell, Codespaces, EC2
                        Instance Connect, ...). See #26923.
  --timeout TIMEOUT     HTTP request timeout in seconds for Nous login
                        (default: 15)
  --ca-bundle CA_BUNDLE
                        Path to CA bundle PEM file for Nous TLS verification
  --insecure            Disable TLS verification for Nous login (testing only)

```

## hermes tools

```text
usage: hermes tools [-h] [--summary] {list,disable,enable} ...

Enable, disable, or list tools for CLI, Telegram, Discord, etc. Built-in
toolsets use plain names (e.g. web, memory). MCP tools use server:tool
notation (e.g. github:create_issue). Run 'hermes tools' with no subcommand for
the interactive configuration UI.

positional arguments:
  {list,disable,enable}
    list                Show all tools and their enabled/disabled status
    disable             Disable toolsets or MCP tools
    enable              Enable toolsets or MCP tools

options:
  -h, --help            show this help message and exit
  --summary             Print a summary of enabled tools per platform and exit

```

## hermes gateway

```text
usage: hermes gateway [-h] [--accept-hooks]
                      {run,start,stop,restart,status,install,uninstall,list,setup,migrate-legacy}
                      ...

Manage the messaging gateway (Telegram, Discord, WhatsApp, Weixin, and more)

positional arguments:
  {run,start,stop,restart,status,install,uninstall,list,setup,migrate-legacy}
    run                 Run gateway in foreground (recommended for WSL,
                        Docker, Termux)
    start               Start the installed systemd/launchd background service
    stop                Stop gateway service
    restart             Restart gateway service
    status              Show gateway status
    install             Install gateway as a systemd/launchd background
                        service
    uninstall           Uninstall gateway service
    list                List all profiles and their gateway status
    setup               Configure messaging platforms
    migrate-legacy      Remove legacy hermes.service units from pre-rename
                        installs

options:
  -h, --help            show this help message and exit
  --accept-hooks        Auto-approve unseen shell hooks without a TTY prompt
                        (equivalent to HERMES_ACCEPT_HOOKS=1 /
                        hooks_auto_accept: true).

```

## config files

```text
total 136
drwx------ 12 ubuntu ubuntu  4096 May 19 21:05 .
drwxr-x--- 12 ubuntu ubuntu  4096 May 19 21:03 ..
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 audio_cache
-rw-rw-r--  1 ubuntu ubuntu     0 May 19 21:05 auth.lock
-rw-rw-r--  1 ubuntu ubuntu 57140 May 19 21:05 config.yaml
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 cron
-rw-------  1 ubuntu ubuntu 23061 May 19 21:05 .env
drwxrwxr-x 34 ubuntu ubuntu  4096 May 19 21:05 hermes-agent
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 hooks
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 image_cache
-rw-rw-r--  1 ubuntu ubuntu     4 May 19 21:05 .install_method
drwx------  3 ubuntu ubuntu  4096 May 19 21:05 logs
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 memories
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 pairing
drwx------  2 ubuntu ubuntu  4096 May 19 21:05 sessions
drwx------ 26 ubuntu ubuntu  4096 May 19 21:05 skills
-rw-rw-r--  1 ubuntu ubuntu   537 May 19 21:05 SOUL.md

```
