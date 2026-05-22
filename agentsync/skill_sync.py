#!/usr/bin/env python3
"""Daily automated skill sync between all agents."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()

# Skill directories (source of truth first, then mirrors)
SKILL_SOURCES: dict[str, dict] = {
    "claude-code": {
        "path": HOME / ".claude" / "skills",
        "priority": 1,  # highest priority (source of truth)
        "active": True,
    },
    "claude-desktop-3p": {
        "path": HOME / "Library/Application Support/Claude-3p/claude-code/skills",
        "priority": 2,
        "active": True,
    },
    "workbuddy": {
        "path": HOME / ".workbuddy" / "skills",
        "priority": 3,
        "active": True,
    },
    "hermes": {
        "path": HOME / ".hermes" / "skills",
        "priority": 4,
        "active": True,
    },
}

SYNC_LOG = HOME / ".agentdropone" / "sync.log"


def _hash_dir(path: Path) -> str:
    """Simple hash of directory contents."""
    if not path.exists():
        return ""
    h = hashlib.md5()
    for f in sorted(path.rglob("*")):
        if f.is_file() and ".git" not in str(f) and "__pycache__" not in str(f):
            h.update(str(f.relative_to(path)).encode())
            h.update(str(f.stat().st_mtime).encode())
    return h.hexdigest()[:12]


def _log(msg: str):
    timestamp = datetime.now(timezone.utc).isoformat()[:19]
    line = f"[{timestamp}] {msg}"
    print(line)
    SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SYNC_LOG.open("a") as f:
        f.write(line + "\n")


def _sync_bidirectional(source: Path, target: Path, source_name: str, target_name: str):
    """Sync skills bidirectionally: newer files win, conflicts logged."""
    if not source.exists() or not target.exists():
        return {"synced": 0, "conflicts": 0}

    synced = 0
    conflicts = 0

    for skill_dir in source.iterdir():
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name

        # Skip internal/hidden
        if name.startswith(".") or name.startswith("_"):
            continue

        target_skill = target / name

        if not target_skill.exists():
            # New skill: copy to target
            shutil.copytree(skill_dir, target_skill, dirs_exist_ok=True)
            synced += 1
            _log(f"  + {name}  [{source_name} → {target_name}]")
        else:
            # Compare modification times
            src_mtime = max(
                (f.stat().st_mtime for f in skill_dir.rglob("*") if f.is_file()),
                default=0,
            )
            tgt_mtime = max(
                (f.stat().st_mtime for f in target_skill.rglob("*") if f.is_file()),
                default=0,
            )

            if src_mtime > tgt_mtime + 1:  # 1s buffer
                # Source is newer
                shutil.copytree(skill_dir, target_skill, dirs_exist_ok=True)
                synced += 1
                _log(f"  ^ {name}  [{source_name} → {target_name}]")
            elif tgt_mtime > src_mtime + 1:
                # Target is newer — reverse sync
                shutil.copytree(target_skill, skill_dir, dirs_exist_ok=True)
                synced += 1
                _log(f"  v {name}  [{target_name} → {source_name}]")
            # If equal, skip

    return {"synced": synced, "conflicts": conflicts}


def run_sync(full: bool = False):
    """Execute sync pass. full=True forces full scan even if hash unchanged."""
    _log("Starting skill sync...")

    sources = {
        name: info
        for name, info in SKILL_SOURCES.items()
        if info["active"] and info["path"].exists()
    }

    sorted_sources = sorted(sources.items(), key=lambda x: x[1]["priority"])

    # Quick check: any changes?
    if not full:
        hashes = {name: _hash_dir(info["path"]) for name, info in sorted_sources}
        if len(set(hashes.values())) == 1:
            _log("  All skill dirs identical. Skipping sync.")
            return

    total = {"synced": 0, "conflicts": 0}

    # Bidirectional sync between all pairs
    for i in range(len(sorted_sources) - 1):
        src_name, src_info = sorted_sources[i]
        for j in range(i + 1, len(sorted_sources)):
            tgt_name, tgt_info = sorted_sources[j]
            result = _sync_bidirectional(
                src_info["path"], tgt_info["path"],
                src_name, tgt_name,
            )
            total["synced"] += result["synced"]
            total["conflicts"] += result["conflicts"]

    _log(f"Sync done: {total['synced']} synced, {total['conflicts']} conflicts")

    # If any skills changed, sync bundle to OneDrive
    if total["synced"] > 0:
        _sync_bundle_to_onedrive()


# ── OneDrive bundle sync ───────────────────────────────────

ONEDRIVE_BUNDLE_DIR = HOME / "Library/CloudStorage/OneDrive-Personal/AgentDropOne"
ONEDRIVE_SKILLS_DIR = ONEDRIVE_BUNDLE_DIR / "skills"


def _sync_bundle_to_onedrive():
    """Push local skill changes to OneDrive bundle. Pull remote changes back."""
    if not ONEDRIVE_BUNDLE_DIR.exists():
        _log("  OneDrive bundle dir not found, skipping remote sync")
        return

    ONEDRIVE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Push: copy skills to OneDrive bundle for other machines
    pushed = 0
    for name, info in SKILL_SOURCES.items():
        if not info["active"] or not info["path"].exists():
            continue

        for skill_dir in info["path"].iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            remote_dir = ONEDRIVE_SKILLS_DIR / skill_dir.name
            if not remote_dir.exists():
                shutil.copytree(skill_dir, remote_dir)
                pushed += 1
            else:
                # Compare times
                src_mtime = max(
                    (f.stat().st_mtime for f in skill_dir.rglob("*") if f.is_file()),
                    default=0,
                )
                rmt_mtime = max(
                    (f.stat().st_mtime for f in remote_dir.rglob("*") if f.is_file()),
                    default=0,
                )
                if src_mtime > rmt_mtime + 1:
                    shutil.copytree(skill_dir, remote_dir, dirs_exist_ok=True)
                    pushed += 1
                elif rmt_mtime > src_mtime + 1:
                    # Pull: OneDrive has newer version (from another machine)
                    shutil.copytree(remote_dir, skill_dir, dirs_exist_ok=True)
                    pushed += 1
                    _log(f"  ⇄ pulled {skill_dir.name} from OneDrive")
                    # Also push to other agents
                    for other_name, other_info in SKILL_SOURCES.items():
                        if other_name != name and other_info["active"]:
                            other_target = other_info["path"] / skill_dir.name
                            if other_target.exists():
                                shutil.copytree(remote_dir, other_target, dirs_exist_ok=True)

    if pushed > 0:
        # Trigger snapshot of config files too (via sync-daemon)
        _log(f"  Bundle updated: {pushed} skills synced to OneDrive")

        # Try to run snapshot if sync-daemon is available
        sync_py = Path(__file__).parent.parent / "onesync-skills/sync-daemon/sync.py"
        if sync_py.exists():
            try:
                subprocess.run(
                    [sys.executable, str(sync_py), "snapshot"],
                    capture_output=True, timeout=30,
                )
                _log(f"  Config snapshot updated in OneDrive")
            except:
                pass


def setup_cron(interval: str = "daily"):
    """Install as a cron job."""
    script = Path(__file__).resolve()
    cmd = f"cd {script.parent.parent} && {sys.executable} -m agentsync.skill_sync --cron"

    if interval == "hourly":
        schedule = "0 * * * *"
    elif interval == "daily":
        schedule = "0 9 * * *"  # 9am daily
    else:
        schedule = interval

    cron_line = f"{schedule} {cmd} > /tmp/agentdropone-sync.log 2>&1"

    # Get current crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    current = result.stdout if result.returncode == 0 else ""

    # Check if already there
    if "agentdropone-sync" in current:
        _log("Cron job already installed.")
        return

    new_cron = current.strip() + "\n" + cron_line + "\n"
    subprocess.run(["crontab"], input=new_cron, text=True)
    _log(f"Cron job installed: {schedule}")


def setup_launchd():
    """Install as a macOS LaunchAgent (runs hourly)."""
    plist_path = HOME / "Library/LaunchAgents/com.agentdropone.sync.plist"
    script = Path(__file__).resolve()

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentdropone.sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{script}</string>
        <string>--cron</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>/tmp/agentdropone-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/agentdropone-sync.err</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""

    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist)
    subprocess.run(["launchctl", "load", str(plist_path)], check=False)
    _log(f"LaunchAgent installed: {plist_path}")


# ── CLI ────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="agentdropone-sync: Daily skill sync")
    parser.add_argument("--cron", action="store_true", help="Run silent (for cron/launchd)")
    parser.add_argument("--full", action="store_true", help="Force full sync")
    parser.add_argument("--install", action="store_true", help="Install as cron job")
    parser.add_argument("--install-launchd", action="store_true", help="Install as macOS LaunchAgent")

    args = parser.parse_args()

    if args.install:
        setup_cron("daily")
        return

    if args.install_launchd:
        setup_launchd()
        return

    run_sync(full=args.full)


if __name__ == "__main__":
    main()
