---
name: workspace-setup
description: >
  Auto-setup dev workspace on a new machine. Installs CLI tools, restores git/npm/pip/Docker configs,
  and connects to remote services. Drop this skill on a new machine and let the agent do everything.
version: 0.1.0
---

# workspace-setup

One-command workspace bootstrap for a new machine.

## Usage

On a NEW machine, tell your agent:
> "Set up my workspace using workspace-setup"

The agent will:
1. Read `workspace-manifest.json` from the migration bundle
2. Install all listed tools (brew, npm, pip, etc.)
3. Restore git config, SSH keys, Docker config
4. Verify everything works

## What it restores

| Category | What |
|----------|------|
| Homebrew | Formulae + casks list (auto-install) |
| npm | Global packages |
| pip | Python packages |
| Git | user.name, user.email, .gitconfig |
| SSH | Public keys + config |
| Docker | daemon config, registries |
| CLI tools | gh, kubectl, cloudflared, colima, etc. |

## Commands

```bash
# Export workspace config from current machine
python3 workspace_export.py -o workspace-manifest.json

# On new machine: read manifest and setup
python3 workspace_setup.py workspace-manifest.json

# Dry run (preview only)
python3 workspace_setup.py workspace-manifest.json --dry-run
```

## Self-packaging

This skill can export itself + workspace data into a zip:
```bash
python3 workspace_export.py --self-pack -o workspace-migration.zip
```

The zip contains:
- SKILL.md (this file)
- workspace-manifest.json (all tool lists + configs)
- .gitconfig, .npmrc, etc.
