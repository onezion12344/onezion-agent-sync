---
name: full-migrate
description: >
  Master migration skill. Bundles workspace + agent sync + cookies into ONE zip.
  Drop this zip on a new machine, tell the agent "restore everything", done.
version: 0.1.0
---

# full-migrate

One zip. One command. Full machine migration.

## What's in the bundle

```
full-migration.zip
├── workspace/           # Layer 1: Dev environment
│   └── workspace-manifest.json (brew, npm, pip, git, SSH, Docker)
├── agent-sync/          # Layer 2: Agent configs + secrets
│   ├── secrets-export.json (24+ API keys)
│   ├── hermes/backup.zip
│   ├── openclaw/backup.zip
│   ├── claude-code/ (settings, skills, memory)
│   └── ... other agents
├── cookies/             # Layer 3: Login states
│   └── cookie-migration.zip (gh, fly, superhuman, chrome)
└── meta.json            # Bundle metadata
```

## Usage

### Export (current machine)
```bash
python3 full_export.py -o ~/Desktop/full-migration.zip
```

### Import (new machine)
```bash
python3 full_import.py full-migration.zip
python3 full_import.py full-migration.zip --dry-run  # preview first
```

### Or tell your agent
> "Restore my full migration from full-migration.zip"

The agent reads this SKILL.md, knows the structure, and does everything.

## Self-packaging

Every sub-skill can self-package. This skill bundles them all:
- workspace-setup exports workspace-manifest.json
- onezion-agent-sync exports secrets + agent configs
- cookie-manager exports login states
- full-migrate zips everything together
