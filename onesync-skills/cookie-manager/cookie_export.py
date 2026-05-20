#!/usr/bin/env python3
"""Export browser cookies, OAuth tokens, and CLI auth states."""

from __future__ import annotations
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()

# Files/dirs to export for login state
AUTH_SOURCES = [
    # (source_path_relative_to_home, description)
    (".config/gh/hosts.yml", "GitHub CLI OAuth token"),
    (".config/gh/config.yml", "GitHub CLI config"),
    (".fly/config.yml", "Fly.io auth tokens"),
    (".config/superhuman-cli/tokens.json", "Superhuman OAuth tokens"),
    (".config/rclone/rclone.conf", "rclone cloud storage tokens"),
    (".docker/config.json", "Docker registry auth"),
    (".netrc", "General credential store"),
    (".aws/credentials", "AWS credentials"),
    (".config/gcloud/", "Google Cloud SDK"),
]

# Chrome profile dirs (cookies are in Default/Cookies — SQLite)
CHROME_PATH = HOME / "Library/Application Support/Google/Chrome/Default"
CHROME_AUTH_FILES = [
    "Cookies",
    "Login Data",
    "Web Data",
    "Local Storage/leveldb",
]


def export_cookies(output_path: str):
    out = Path(output_path)
    exported = []

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add metadata
        meta = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "machine": Path.home().name,
            "type": "cookie-manager-export",
        }
        zf.writestr("meta.json", json.dumps(meta, indent=2))

        # Export auth files
        for rel_path, desc in AUTH_SOURCES:
            src = HOME / rel_path
            if src.is_file():
                zf.write(src, f"auth/{rel_path}")
                exported.append(f"  [auth] {rel_path} — {desc}")
            elif src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        zf.write(f, f"auth/{rel_path}{f.relative_to(src)}")
                exported.append(f"  [auth] {rel_path}/ — {desc}")

        # Export Chrome auth-related files
        if CHROME_PATH.exists():
            for cf in CHROME_AUTH_FILES:
                src = CHROME_PATH / cf
                if src.is_file():
                    zf.write(src, f"chrome/{cf}")
                    exported.append(f"  [chrome] {cf}")
                elif src.is_dir():
                    for f in src.rglob("*"):
                        if f.is_file():
                            zf.write(f, f"chrome/{cf}/{f.relative_to(src)}")
                    exported.append(f"  [chrome] {cf}/")

    print(f"\nExported {len(exported)} items to {out}:\n")
    for e in exported:
        print(e)
    print(f"\nTotal: {out.stat().st_size / 1024:.0f} KB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="cookie-migration.zip")
    args = parser.parse_args()
    export_cookies(args.output)


if __name__ == "__main__":
    main()
