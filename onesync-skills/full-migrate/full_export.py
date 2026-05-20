#!/usr/bin/env python3
"""Master export: bundle workspace + agent-sync + cookies into one zip."""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime, timezone

SKILL_DIR = Path(__file__).parent
ONESYNC_ROOT = SKILL_DIR.parent.parent  # onezion-agent-sync/
HOME = Path.home()


def run_script(script_path: str, args: list[str], timeout=120):
    """Run a Python script as subprocess."""
    cmd = ["python3", script_path] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        print(r.stdout)
        if r.stderr:
            print(r.stderr[:500])
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Timeout running {script_path}")
        return False


def full_export(output_path: str):
    out = Path(output_path)
    staging = Path("/tmp/full-migrate-export")
    if staging.exists():
        import shutil
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    print("=" * 60)
    print("FULL MIGRATION EXPORT")
    print("=" * 60)

    # Layer 1: Workspace
    print("\n[1/3] Workspace Setup...")
    ws_export = SKILL_DIR.parent / "workspace-setup" / "workspace_export.py"
    if ws_export.exists():
        run_script(str(ws_export), ["-o", str(staging / "workspace-manifest.json")])
    else:
        print("  workspace_export.py not found, skipping")

    # Layer 2: Agent Sync
    print("\n[2/3] Agent Sync...")
    agent_sync_cli = ONESYNC_ROOT / "agentsync" / "cli.py"
    if agent_sync_cli.exists():
        # Export secrets
        print("  Exporting secrets...")
        run_script("-m", ["agentsync.cli", "export-secrets",
                          "-o", str(staging / "secrets-export.json")],
                   cwd=str(ONESYNC_ROOT))
        # Run orchestration for agent configs
        print("  Orchestrating agent exports...")
        run_script("-m", ["agentsync.cli", "orchestrate",
                          "-o", str(staging / "agent-sync")],
                   cwd=str(ONESYNC_ROOT), timeout=180)
    else:
        # Fallback: check if previous export exists
        prev = HOME / "Desktop" / "agent-migration"
        if prev.exists():
            import shutil
            shutil.copytree(prev, staging / "agent-sync")
            print(f"  Used previous export from {prev}")

    # Layer 3: Cookies
    print("\n[3/3] Cookies & Login States...")
    cookie_export = SKILL_DIR.parent / "cookie-manager" / "cookie_export.py"
    if cookie_export.exists():
        run_script(str(cookie_export), ["-o", str(staging / "cookie-migration.zip")])
    else:
        print("  cookie_export.py not found, skipping")

    # Generate meta.json
    meta = {
        "version": "1.0.0",
        "type": "full-migration",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "machine": os.uname().nodename,
        "layers": {
            "workspace": (staging / "workspace-manifest.json").exists(),
            "agent_sync": (staging / "secrets-export.json").exists(),
            "cookies": (staging / "cookie-migration.zip").exists(),
        },
    }
    (staging / "meta.json").write_text(json.dumps(meta, indent=2))

    # Bundle into final zip
    print("\nBundling...")
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in staging.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(staging))

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"EXPORT COMPLETE: {out} ({size_mb:.1f} MB)")
    print(f"{'=' * 60}")

    # Cleanup
    import shutil
    shutil.rmtree(staging, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Full migration export")
    parser.add_argument("-o", "--output", default=str(HOME / "Desktop" / "full-migration.zip"))
    args = parser.parse_args()
    full_export(args.output)


if __name__ == "__main__":
    main()
