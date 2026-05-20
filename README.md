<div align="center">

# AgentDropOne

**One zip. One command. Full agent workspace.**

*Drop your entire AI agent environment onto any machine and watch it rebuild itself.*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/onezion12344/AgentDropOne?style=social)](https://github.com/onezion12344/AgentDropOne)

</div>

---

## What is this?

AgentDropOne is a **self-bootstrapping migration tool** for AI agent workspaces. It packages your entire development environment — agents, configs, secrets, skills, MCP servers, login states — into a single zip file. Drop it on a new machine, run one command, and everything comes back.

```
┌─────────────────────────────────────────────────────┐
│  AgentDropOne                                       │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Workspace │  │  Agent   │  │   Cookies &      │  │
│  │ Layer 1   │  │  Layer 2 │  │   Login States   │  │
│  │           │  │          │  │   Layer 3         │  │
│  │ brew      │  │ secrets  │  │                   │  │
│  │ npm       │  │ hermes   │  │ gh, fly, chrome   │  │
│  │ pip       │  │ openclaw │  │ superhuman, etc   │  │
│  │ git/ssh   │  │ claude   │  │                   │  │
│  │ docker    │  │ gemini   │  │                   │  │
│  │ 183 pkgs  │  │ codex    │  │                   │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│          →  full-migration.zip (20 MB)  →           │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Export (current machine)

```bash
# Full export — everything in one zip
python3 agentdropone-setup.py full-migration.zip --export
```

### Import (new machine)

```bash
# One command to rule them all
python3 agentdropone-setup.py full-migration.zip

# Preview first (recommended)
python3 agentdropone-setup.py full-migration.zip --dry-run
```

That's it. 9 steps, fully automated:

```
[1] Extract migration bundle        ✓
[2] Read metadata                   ✓
[3] Install prerequisites           ✓  (brew, node, python)
[4] Restore workspace tools         ✓  (183 brew, 28 npm, git, SSH, Docker)
[5] Install agents                  ✓  (Claude Code, Hermes, OpenClaw, Gemini...)
[6] Restore agent configs           ✓  (settings, skills, memory, MCP)
[7] Import secrets                  ✓  (24+ API keys)
[8] Restore login states            ✓  (GitHub, Fly.io, Chrome, Superhuman)
[9] Verify installation             ✓
```

## What's Inside

### Layer 1: Workspace
Your dev environment, fully reproducible.
- **183** Homebrew formulae + **52** casks
- **28** npm global packages
- Git config, SSH keys, Docker config
- CLI tools (gh, kubectl, cloudflared, colima...)

### Layer 2: Agent Sync
All your AI agents, their configs, and secrets.
- **24+** API keys (Keychain, shell, .env, config files)
- Agent configs: Claude Code, Hermes, OpenClaw, Gemini CLI, Codex, WorkBuddy...
- Skills, memory files, MCP server configurations
- Auto-discovery from GitHub docs

### Layer 3: Login States
Your sessions, cookies, and OAuth tokens.
- GitHub CLI auth (gh)
- Fly.io tokens
- Superhuman OAuth
- rclone cloud storage tokens
- Docker registry auth
- Chrome cookies & login data

## Tools

| Command | Description |
|---------|-------------|
| `python3 agentdropone-setup.py bundle.zip` | **Full setup** on new machine |
| `python3 agentdropone-setup.py bundle.zip --dry-run` | Preview without executing |
| `python3 -m agentsync.cli scan` | Discover all secrets on this machine |
| `python3 -m agentsync.cli export-secrets` | Export secrets to JSON |
| `python3 -m agentsync.cli import secrets.json` | Import secrets on new machine |
| `python3 -m agentsync.cli discover` | Scan for installed agents |
| `python3 -m agentsync.cli orchestrate` | Auto-export from all agents |
| `python3 -m agentsync.cli docs --all` | Discover agent configs from GitHub |

## Sync Daemon

Keep configs in sync across machines via cloud storage:

```bash
# Snapshot current configs (auto-strips secrets)
python3 sync.py snapshot

# Watch for changes (every 30s)
python3 sync.py watch

# Apply changes from other machine
python3 sync.py apply

# Use any cloud provider via rclone
python3 sync.py setup-remote "onedrive:onezion-sync"
python3 sync.py setup-remote "gdrive:agentdropone"
python3 sync.py push
python3 sync.py pull
```

Works with: **OneDrive**, **Google Drive**, **Dropbox**, **S3**, **Backblaze B2**, **WebDAV**, and 40+ other providers via rclone.

## Architecture

```
AgentDropOne/
├── agentsync/                  # Core Python modules
│   ├── secrets.py              # 24+ API key auto-discovery (5 sources)
│   ├── orchestrator.py         # Agent orchestration (auto-export + manual guide)
│   ├── registry.py             # 10 known agents with export methods
│   ├── docs.py                 # GitHub docs crawler for config discovery
│   └── cli.py                  # CLI entry point
├── onesync-skills/             # Independent skills
│   ├── workspace-setup/        # brew/npm/pip/git/SSH/Docker
│   ├── cookie-manager/         # Browser cookies + OAuth tokens
│   ├── sync-daemon/            # Config sync via cloud storage
│   └── full-migrate/           # Bundler + setup.py
├── SKILL.md                    # Agent-readable skill file
└── pyproject.toml
```

## Supported Agents

| Agent | Auto-Export | Config Path |
|-------|------------|-------------|
| Hermes Agent | `hermes backup` | `~/.hermes/config.yaml` |
| OpenClaw | `openclaw backup create` | `~/.openclaw/openclaw.json` |
| Claude Code | Manual | `~/.claude/settings.json` |
| Claude Desktop | Manual | `~/Library/Application Support/Claude/` |
| Gemini CLI | Manual | `~/.gemini/settings.json` |
| OpenAI Codex | Manual | `~/.codex/config.toml` |
| WorkBuddy | Manual | `~/.workbuddy/mcp.json` |
| Goose | Manual | `~/.config/goose/config.yaml` |
| OpenCode | Manual | `~/.config/opencode/opencode.json` |

Add more in `agentsync/registry.py`.

## For Agent Developers

This tool is designed to be used **by agents, for agents**. Install it as a skill in any agent platform:

1. Clone this repo into your agent's skills directory
2. The agent reads `SKILL.md` to understand what it can do
3. User says "migrate my setup" → agent runs the pipeline automatically

The skill is **platform-agnostic** — it works with Claude Code, OpenClaw, Hermes, WorkBuddy, or any agent that can run Python scripts.

## Philosophy

> **Glue code, done right.**

We don't rebuild what already exists. We connect:
- **rclone** for cloud storage (40+ providers)
- **Homebrew** for package management
- **Hermes/OpenClaw** native backup for agent data
- **macOS Keychain** for secret storage
- **GitHub** for documentation discovery

AgentDropOne is the orchestration layer that makes all these tools work together for one purpose: **your workspace, anywhere, in seconds**.

## Requirements

- Python 3.9+ (no external dependencies)
- macOS (Linux support planned)
- Cloud storage client (OneDrive, Google Drive, Dropbox, or rclone)

## License

MIT

---

<div align="center">

**[Documentation](SKILL.md)** · **[Issues](https://github.com/onezion12344/AgentDropOne/issues)**

Built with the philosophy: *Drop one zip, get your whole world back.*

</div>
