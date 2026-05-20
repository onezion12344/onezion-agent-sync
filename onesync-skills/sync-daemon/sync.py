#!/usr/bin/env python3
"""
onezion-sync: Lightweight config sync via cloud storage.

Watches agent config directories for changes, snapshots to a sync folder
inside OneDrive. Other machine picks up automatically.

Usage:
    python3 sync.py watch       # Start watching (foreground)
    python3 sync.py snapshot    # One-time snapshot
    python3 sync.py apply       # Apply incoming changes
    python3 sync.py status      # Show sync status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()

# Where the sync folder lives (inside OneDrive)
# Auto-detect OneDrive path
def _find_sync_dir() -> Path:
    candidates = [
        HOME / "Library/CloudStorage/OneDrive-Personal/.onezion-sync",
        HOME / "OneDrive/.onezion-sync",
        HOME / ".onezion-sync",  # fallback
    ]
    for c in candidates:
        if c.parent.exists():
            return c
    return candidates[-1]

SYNC_DIR = _find_sync_dir()

# rclone remote name (user configures this)
# Supports: OneDrive, Google Drive, Dropbox, S3, B2, WebDAV, etc.
RCLONE_REMOTE = os.environ.get("ONEZION_SYNC_REMOTE", "")  # e.g. "onedrive:onezion-sync"

# Files to watch (relative to HOME)
WATCH_TARGETS = [
    # (relative_path, is_dir, sanitize)
    (".claude/settings.json", False, True),
    (".claude/settings.local.json", False, True),
    (".claude/config.json", False, False),
    (".hermes/config.yaml", False, True),
    (".openclaw/openclaw.json", False, True),
    (".gemini/settings.json", False, True),
    (".gemini/config/config.json", False, False),
    (".workbuddy/mcp.json", False, False),
    (".config/goose/config.yaml", False, False),
    (".config/opencode/opencode.json", False, False),
    (".codex/config.toml", False, False),
]

# Keys to strip when sanitizing
SECRET_KEYS = {
    "apiKey", "api_key", "token", "secret", "password",
    "access_token", "refresh_token", "id_token",
    "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY",
}


def _file_hash(path: Path) -> str:
    """Fast hash of file contents."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()[:12]


def _sanitize_json(data: dict) -> dict:
    """Remove secret values from JSON, keep structure."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if k in SECRET_KEYS and isinstance(v, str) and len(v) > 5
            else _sanitize_json(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_sanitize_json(item) for item in data]
    return data


def _sanitize_file(src: Path, dst: Path):
    """Copy file with secrets redacted."""
    try:
        if src.suffix == ".json":
            data = json.loads(src.read_text())
            sanitized = _sanitize_json(data)
            dst.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False))
        elif src.suffix in (".yaml", ".yml"):
            # Simple redaction for YAML
            text = src.read_text()
            for key in SECRET_KEYS:
                text = text.replace(f"{key}:", f"{key}: ***REDACTED***")
            dst.write_text(text)
        else:
            # Copy as-is for non-sensitive files
            shutil.copy2(src, dst)
    except Exception:
        shutil.copy2(src, dst)


def _read_manifest() -> dict:
    manifest_path = SYNC_DIR / "manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except:
            pass
    return {"version": "1.0", "files": {}, "machine": os.uname().nodename}


def _write_manifest(manifest: dict):
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["machine"] = os.uname().nodename
    (SYNC_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))


# ── Commands ───────────────────────────────────────────────

def cmd_snapshot():
    """Take a snapshot of all watched configs."""
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest()
    changes = 0

    for rel_path, is_dir, sanitize in WATCH_TARGETS:
        src = HOME / rel_path
        if not src.exists():
            continue

        current_hash = _file_hash(src)
        old_hash = manifest["files"].get(rel_path, {}).get("hash", "")

        if current_hash == old_hash:
            continue  # No change

        # File changed, snapshot it
        dst = SYNC_DIR / rel_path.replace("/", "__")
        if sanitize:
            _sanitize_file(src, dst)
        else:
            shutil.copy2(src, dst)

        manifest["files"][rel_path] = {
            "hash": current_hash,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "sanitized": sanitize,
        }
        changes += 1
        print(f"  Synced: {rel_path}")

    _write_manifest(manifest)
    print(f"\n{changes} file(s) synced to {SYNC_DIR}")


def cmd_watch(interval: int = 30):
    """Watch for changes and sync periodically."""
    print(f"Watching for config changes every {interval}s...")
    print(f"Sync folder: {SYNC_DIR}")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            cmd_snapshot()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped watching.")
            break


def cmd_apply():
    """Apply changes from the sync folder (from another machine)."""
    manifest_path = SYNC_DIR / "manifest.json"
    if not manifest_path.exists():
        print("No sync data found.")
        return

    manifest = _read_manifest()
    local_manifest = _read_local_state()
    applied = 0

    for rel_path, info in manifest.get("files", {}).items():
        remote_hash = info.get("hash", "")
        local_hash = local_manifest.get(rel_path, {}).get("hash", "")

        if remote_hash == local_hash:
            continue  # Already up to date

        src = SYNC_DIR / rel_path.replace("/", "__")
        if not src.exists():
            continue

        dst = HOME / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)

        if info.get("sanitized"):
            # Can't apply sanitized files directly, skip
            print(f"  Skipped (sanitized): {rel_path}")
            continue

        shutil.copy2(src, dst)
        local_manifest[rel_path] = {"hash": remote_hash, "applied_at": datetime.now(timezone.utc).isoformat()}
        applied += 1
        print(f"  Applied: {rel_path}")

    _save_local_state(local_manifest)
    print(f"\n{applied} file(s) applied.")


def cmd_status():
    """Show sync status."""
    manifest_path = SYNC_DIR / "manifest.json"
    if not manifest_path.exists():
        print("No sync data found. Run 'snapshot' first.")
        return

    manifest = _read_manifest()
    print(f"\nSync folder: {SYNC_DIR}")
    print(f"Last updated: {manifest.get('updated_at', 'never')}")
    print(f"Machine: {manifest.get('machine', 'unknown')}")
    print(f"\nTracked files ({len(manifest.get('files', {}))}):")

    for rel_path, info in manifest.get("files", {}).items():
        hash_val = info.get("hash", "?")
        synced = info.get("synced_at", "?")[:19]
        sanitized = " [sanitized]" if info.get("sanitized") else ""
        print(f"  {rel_path:<45} {hash_val}  {synced}{sanitized}")


def _read_local_state() -> dict:
    state_path = SYNC_DIR / ".local-state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except:
            pass
    return {}


def _save_local_state(state: dict):
    (SYNC_DIR / ".local-state.json").write_text(json.dumps(state, indent=2))


# ── rclone gateway ─────────────────────────────────────────

def _get_rclone_remote() -> str:
    """Get rclone remote from env, config, or auto-detect."""
    if RCLONE_REMOTE:
        return RCLONE_REMOTE

    # Check config file
    config_file = SYNC_DIR / "rclone-remote.txt"
    if config_file.exists():
        return config_file.read_text().strip()

    # Auto-detect: check if OneDrive is available
    od_path = HOME / "Library/CloudStorage/OneDrive-Personal"
    if od_path.exists():
        return ""  # Use local OneDrive folder directly

    return ""


def cmd_push():
    """Push local sync folder to cloud storage via rclone."""
    remote = _get_rclone_remote()
    if not remote:
        print("No rclone remote configured.")
        print("Set ONEZION_SYNC_REMOTE env var or create ~/.onezion-sync/rclone-remote.txt")
        print("Examples:")
        print("  export ONEZION_SYNC_REMOTE='onedrive:onezion-sync'")
        print("  export ONEZION_SYNC_REMOTE='gdrive:onezion-sync'")
        print("  export ONEZION_SYNC_REMOTE='dropbox:onezion-sync'")
        print("  export ONEZION_SYNC_REMOTE='b2:my-bucket/onezion-sync'")
        return

    print(f"Pushing to {remote}...")
    cmd = f"rclone sync '{SYNC_DIR}' '{remote}' --progress"
    r = subprocess.run(cmd, shell=True, timeout=120)
    if r.returncode == 0:
        print("Push complete.")
    else:
        print("Push failed. Check rclone config.")


def cmd_pull():
    """Pull from cloud storage to local sync folder via rclone."""
    remote = _get_rclone_remote()
    if not remote:
        print("No rclone remote configured. Use 'push --setup' first.")
        return

    print(f"Pulling from {remote}...")
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cmd = f"rclone sync '{remote}' '{SYNC_DIR}' --progress"
    r = subprocess.run(cmd, shell=True, timeout=120)
    if r.returncode == 0:
        print("Pull complete. Run 'apply' to restore configs.")
    else:
        print("Pull failed. Check rclone config.")


def cmd_setup_remote(remote: str):
    """Configure rclone remote for sync."""
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    config_file = SYNC_DIR / "rclone-remote.txt"
    config_file.write_text(remote)
    print(f"Configured sync remote: {remote}")
    print(f"Saved to: {config_file}")

    # Test connection
    print("Testing connection...")
    r = subprocess.run(f"rclone lsd '{remote}' 2>&1 | head -5", shell=True, capture_output=True, text=True)
    if r.returncode == 0:
        print("Connection OK!")
    else:
        print(f"Connection test: {r.stdout[:200]}")


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="onezion-sync: Config sync via cloud storage gateway",
        epilog="Supports 40+ providers via rclone: OneDrive, Google Drive, Dropbox, S3, B2, WebDAV, etc."
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("snapshot", help="Take a one-time snapshot of all configs")
    p_watch = sub.add_parser("watch", help="Watch for changes (foreground)")
    p_watch.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    sub.add_parser("apply", help="Apply incoming changes from other machine")
    sub.add_parser("status", help="Show sync status")
    sub.add_parser("push", help="Push to cloud storage via rclone")
    sub.add_parser("pull", help="Pull from cloud storage via rclone")
    p_setup = sub.add_parser("setup-remote", help="Configure cloud storage provider")
    p_setup.add_argument("remote", help="rclone remote (e.g. 'onedrive:onezion-sync', 'gdrive:onezion-sync')")

    args = parser.parse_args()

    if args.command == "snapshot":
        cmd_snapshot()
    elif args.command == "watch":
        cmd_watch(args.interval)
    elif args.command == "apply":
        cmd_apply()
    elif args.command == "status":
        cmd_status()
    elif args.command == "push":
        cmd_push()
    elif args.command == "pull":
        cmd_pull()
    elif args.command == "setup-remote":
        cmd_setup_remote(args.remote)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
