---
name: cookie-manager
description: >
  Export and import browser cookies, OAuth tokens, and login sessions.
  Supports Chrome, Firefox, and CLI tool auth (gh, flyctl, etc.).
  One-click login state migration between machines.
version: 0.1.0
---

# cookie-manager

Migrate login states without re-authenticating everything.

## What it captures

| Source | What | Auto? |
|--------|------|-------|
| Chrome | Cookies, localStorage, sessionStorage | Copy profile |
| Firefox | Cookies, logins | Copy profile |
| gh (GitHub CLI) | OAuth token | Copy ~/.config/gh/ |
| flyctl | Auth token | Copy ~/.fly/ |
| Superhuman | OAuth tokens | Copy ~/.config/superhuman-cli/ |
| Docker | Registry auth | Copy ~/.docker/ |
| rclone | Cloud storage tokens | Copy ~/.config/rclone/ |

## Usage

```bash
# Export all login states
python3 cookie_export.py -o cookie-migration.zip

# Import on new machine
python3 cookie_import.py cookie-migration.zip
```

## Important notes

- Chrome cookies are in an SQLite database, not directly portable across machines due to encryption
- The export copies the raw files; on the new machine, Chrome may need to be restarted
- OAuth tokens (gh, flyctl) are directly portable — just copy the config files
- Some services detect new machine logins and may require re-verification
