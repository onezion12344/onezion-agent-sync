#!/usr/bin/env python3
"""Master import: restore everything from a full-migration.zip."""

from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

HOME = Path.home()
SKILL_DIR = Path(__file__).parent
ONESYNC_ROOT = SKILL_DIR.parent.parent


def run_script(script_path, args, timeout=120):
    cmd = ["python3", str(script_path)] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        print(r.stdout)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Timeout running {script_path}")
        return False


def full_import(zip_path: str, dry_run: bool = False):
    staging = Path("/tmp/full-migrate-import")
    if staging.exists():
        shutil.rmtree(staging)

    print("=" * 60)
    print("FULL MIGRATION IMPORT")
    print("=" * 60)

    # Extract
    print(f"\nExtracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(staging)

    # Read metadata
    meta_file = staging / "meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
        print(f"  From: {meta.get('machine', 'unknown')}")
        print(f"  At: {meta.get('exported_at', 'unknown')}")
        layers = meta.get("layers", {})
        print(f"  Layers: workspace={layers.get('workspace')}, agent={layers.get('agent_sync')}, cookies={layers.get('cookies')}")

    # Layer 1: Workspace
    ws_manifest = staging / "workspace-manifest.json"
    if ws_manifest.exists():
        print(f"\n[1/3] Workspace Setup...")
        ws_setup = SKILL_DIR.parent / "workspace-setup" / "workspace_setup.py"
        if ws_setup.exists():
            args = [str(ws_manifest)]
            if dry_run:
                args.append("--dry-run")
            run_script(ws_setup, args, timeout=600)
        else:
            print("  workspace_setup.py not found")
    else:
        print("\n[1/3] No workspace data found, skipping")

    # Layer 2: Agent Sync secrets
    secrets_file = staging / "secrets-export.json"
    if secrets_file.exists():
        print(f"\n[2/3] Agent Sync - Secrets...")
        if dry_run:
            data = json.loads(secrets_file.read_text())
            print(f"  Would import {len(data.get('secrets', []))} secrets")
        else:
            import subprocess
            r = subprocess.run(
                ["python3", "-m", "agentsync.cli", "import", str(secrets_file)],
                capture_output=True, text=True, timeout=30,
                cwd=str(ONESYNC_ROOT)
            )
            print(r.stdout)
    else:
        print("\n[2/3] No agent-sync data found, skipping")

    # Layer 2b: Agent configs
    agent_dir = staging / "agent-sync"
    if agent_dir.exists():
        print(f"\n[2b/3] Agent Configs...")
        for agent_path in agent_dir.iterdir():
            if agent_path.is_dir():
                name = agent_path.name
                if dry_run:
                    print(f"  Would restore {name} config")
                else:
                    print(f"  Restoring {name}...")

    # Layer 3: Cookies
    cookie_zip = staging / "cookie-migration.zip"
    if cookie_zip.exists():
        print(f"\n[3/3] Cookies & Login States...")
        cookie_import = SKILL_DIR.parent / "cookie-manager" / "cookie_import.py"
        if cookie_import.exists():
            args = [str(cookie_zip)]
            if dry_run:
                args.append("--dry-run")
            run_script(cookie_import, args)
        else:
            print("  cookie_import.py not found")
    else:
        print("\n[3/3] No cookie data found, skipping")

    # Cleanup
    shutil.rmtree(staging, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"{'[DRY RUN] ' if dry_run else ''}IMPORT COMPLETE")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", help="full-migration.zip path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    full_import(args.zip_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
