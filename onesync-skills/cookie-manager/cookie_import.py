#!/usr/bin/env python3
"""Import browser cookies, OAuth tokens, and CLI auth states."""

from __future__ import annotations
import argparse
import json
import shutil
import zipfile
from pathlib import Path

HOME = Path.home()


def import_cookies(zip_path: str, dry_run: bool = False):
    out_staging = Path("/tmp/cookie-import")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Read metadata
        try:
            meta = json.loads(zf.read("meta.json"))
            print(f"\nImporting from: {meta.get('machine', 'unknown')}")
            print(f"Exported at: {meta.get('exported_at', 'unknown')}\n")
        except:
            print("\nNo metadata found, proceeding...\n")

        # Extract to staging
        if out_staging.exists():
            shutil.rmtree(out_staging)
        zf.extractall(out_staging)

    # Import auth files
    auth_dir = out_staging / "auth"
    if auth_dir.exists():
        for item in auth_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(auth_dir)
                dest = HOME / rel
                if dry_run:
                    print(f"  [dry-run] Would copy {rel} -> {dest}")
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
                    print(f"  Restored: {rel}")

    # Import Chrome files
    chrome_dir = out_staging / "chrome"
    if chrome_dir.exists():
        chrome_dest = Path.home() / "Library/Application Support/Google/Chrome/Default"
        if dry_run:
            print(f"\n  [dry-run] Would restore Chrome profile to {chrome_dest}")
        else:
            print(f"\n  Restoring Chrome auth files...")
            for item in chrome_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(chrome_dir)
                    dest = chrome_dest / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(item, dest)
                        print(f"    {rel}")
                    except Exception as e:
                        print(f"    {rel} (skipped: {e})")
            print("\n  Note: Restart Chrome for changes to take effect.")

    # Cleanup staging
    shutil.rmtree(out_staging, ignore_errors=True)
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Import complete!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", help="cookie-migration.zip path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_cookies(args.zip_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
