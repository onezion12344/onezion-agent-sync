<div align="center">

# AgentDropOne

### One zip. One command. Full agent workspace.

*Drop your entire AI agent environment onto any machine and watch it rebuild itself.*

---

### One-Click Install

```bash
curl -sSL https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.sh | bash
```

That's it. Detects your OS, installs prerequisites, clones AgentDropOne, and asks if you want to create or restore a bundle.

---

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![v0.5.1](https://img.shields.io/badge/version-0.5.1-purple.svg)](https://github.com/onezion12344/AgentDropOne/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Also on ClawHub](https://img.shields.io/badge/ClawHub-ready-ff69b4.svg)](https://clawhub.ai)

[![Landing Page](https://img.shields.io/badge/Landing%20Page-%20→-8A2BE2)](https://onezion12344.github.io/AgentDropOne/)

Made with love by Harry OneZion

</div>

---

## Usage

### New machine (restore)

```bash
curl -sSL https://.../install.sh | bash -s -- bundle.zip
```

Auto-detects OS → installs Python/Node/Git → extracts bundle → asks:

> *Would you like to start Nanobot as your bootstrap agent?* [y/N]

- **y** = Nanobot reads bundle, intelligently guides setup (auto-grabs API key)
- **n** = 9-step deterministic pipeline (no AI needed)

### Old machine (export)

```bash
curl -sSL https://.../install.sh | bash
# → No bundle? Let's create one!
# → Scans all agents, exports 24 secrets, copies configs
# → Saves to Desktop/agentdropone-bundle.zip
```

### Windows

```powershell
irm https://raw.githubusercontent.com/onezion12344/AgentDropOne/main/install.ps1 | iex
```

---

## What's in the bundle

```
agentdropone-bundle.zip (~224 MB)
├── workspace-manifest.json    183 brew, 31 npm, 565 pip, git, SSH, Docker
├── secrets-export.json         24 API keys (auto-discovered)
├── hermes/backup.zip           Auto-exported via CLI
├── openclaw/backup.zip         Auto-exported via CLI
├── claude-code/                Full configs + 190 skills + memory
├── gemini-cli/                 Firebase configs
├── chat-history/               913 sessions from 13 agents
├── cookie-migration.zip        gh, fly, superhuman, rclone, Chrome
└── meta.json
```

---

## Daily Sync

Runs automatically every hour:
```
Claude Code ←→ WorkBuddy ←→ Hermes ←→ OneDrive
```

First run: **364 skills synced, 0 conflicts**.

```bash
python3 -m agentsync.skill_sync              # Manual run
python3 -m agentsync.skill_sync --install-launchd  # Install hourly
```

---

## CLI Reference

| Command | Does |
|---------|------|
| `install.sh` | One-click full install |
| `python3 -m agentsync.cli scan` | Discover all secrets |
| `python3 -m agentsync.cli chat-export` | Export 913 sessions from 13 agents |
| `python3 -m agentsync.cli discover` | Scan installed agents |
| `python3 -m agentsync.cli orchestrate` | Auto-export all agents |
| `python3 -m agentsync.cli docs --all` | Discover agent configs from GitHub |

---

## Architecture

```
lib/nanobot/          HKUDS bootstrap mini-agent (2.2MB)
agentsync/            Secrets, orchestrator, sync, chat-export, docs
onesync-skills/       workspace-setup, cookie-manager, sync-daemon, full-migrate
install.sh             Bash one-click installer
install.ps1            Windows PowerShell installer
docs/                  GitHub Pages landing page
```

Agent-first. Not script-first. Skills work on any agent that runs Python.

---

## License

MIT — Made with love by Harry OneZion
