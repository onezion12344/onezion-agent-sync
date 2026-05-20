#!/usr/bin/env python3
"""Import workspace config on a new machine."""

from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

HOME = Path.home()


def run(cmd, timeout=60):
    print(f"    $ {cmd}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return True
        else:
            print(f"    Error: {r.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"    Timeout after {timeout}s")
        return False


def setup_workspace(manifest_path: str, dry_run: bool = False):
    data = json.loads(Path(manifest_path).read_text())

    print(f"\nSetting up workspace from: {data.get('machine', 'unknown')}")
    print(f"Exported: {data.get('exported_at', 'unknown')}\n")

    # Homebrew
    brew_formulae = data.get("brew_formulae", [])
    brew_casks = data.get("brew_casks", [])
    if brew_formulae or brew_casks:
        print(f"1. Homebrew ({len(brew_formulae)} formulae, {len(brew_casks)} casks)")
        if not dry_run:
            if brew_formulae:
                run(f"brew install {' '.join(brew_formulae[:20])}", timeout=300)
                if len(brew_formulae) > 20:
                    print(f"    ... and {len(brew_formulae)-20} more (run again to continue)")
            if brew_casks:
                run(f"brew install --cask {' '.join(brew_casks[:20])}", timeout=300)
        else:
            for f in brew_formulae[:5]:
                print(f"    brew install {f}")
            if len(brew_formulae) > 5:
                print(f"    ... and {len(brew_formulae)-5} more")

    # npm
    npm_packages = data.get("npm_packages", [])
    if npm_packages:
        print(f"\n2. npm ({len(npm_packages)} packages)")
        if not dry_run:
            for pkg in npm_packages:
                run(f"npm install -g {pkg}", timeout=30)
        else:
            for pkg in npm_packages[:5]:
                print(f"    npm install -g {pkg}")

    # pip
    pip_packages = data.get("pip_packages", [])
    if pip_packages:
        print(f"\n3. pip ({len(pip_packages)} packages)")
        if not dry_run:
            run(f"pip install {' '.join(pip_packages[:20])}", timeout=120)
        else:
            for pkg in pip_packages[:5]:
                print(f"    pip install {pkg}")

    # Git
    git_config = data.get("git_config", {})
    if git_config:
        print(f"\n4. Git config")
        if not dry_run:
            for key, val in git_config.items():
                if val:
                    run(f"git config --global {key} \"{val}\"")
        else:
            for key, val in git_config.items():
                if val:
                    print(f"    git config --global {key} \"{val}\"")

    # SSH keys
    ssh_keys = data.get("ssh_keys", [])
    if ssh_keys:
        print(f"\n5. SSH keys ({len(ssh_keys)} keys)")
        ssh_dir = HOME / ".ssh"
        if not dry_run:
            ssh_dir.mkdir(mode=0o700, exist_ok=True)
            for key in ssh_keys:
                key_path = ssh_dir / key["name"]
                key_path.write_text(key["content"])
                key_path.chmod(0o644)
                print(f"    Wrote {key_path}")
        else:
            for key in ssh_keys:
                print(f"    Write ~/.ssh/{key['name']}")

    # Docker config
    docker_config = data.get("docker_config")
    if docker_config:
        print(f"\n6. Docker config")
        if not dry_run:
            docker_dir = HOME / ".docker"
            docker_dir.mkdir(exist_ok=True)
            (docker_dir / "config.json").write_text(json.dumps(docker_config))
            print(f"    Wrote ~/.docker/config.json")
        else:
            print(f"    Write ~/.docker/config.json")

    # npmrc
    npmrc = data.get("npmrc")
    if npmrc:
        print(f"\n7. .npmrc")
        if not dry_run:
            (HOME / ".npmrc").write_text(npmrc)
            print(f"    Wrote ~/.npmrc")
        else:
            print(f"    Write ~/.npmrc")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Workspace setup complete!")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", help="workspace-manifest.json path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_workspace(args.manifest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
