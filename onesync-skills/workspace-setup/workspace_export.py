#!/usr/bin/env python3
"""Export workspace config: brew, npm, pip, git, SSH, Docker, CLI tools."""

from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except:
        return ""


def export_workspace():
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "machine": os.uname().nodename,
        "os": f"{os.uname().sysname} {os.uname().release}",
    }

    # Homebrew
    print("  Homebrew...")
    data["brew_formulae"] = run("brew list --formula").split("\n") if run("which brew") else []
    data["brew_casks"] = run("brew list --cask").split("\n") if run("which brew") else []
    data["brew_taps"] = run("brew tap").split("\n") if run("which brew") else []

    # npm
    print("  npm...")
    npm_list = run("npm list -g --depth=0 --json 2>/dev/null")
    if npm_list:
        try:
            npm_data = json.loads(npm_list)
            data["npm_packages"] = list(npm_data.get("dependencies", {}).keys())
        except:
            data["npm_packages"] = []
    else:
        data["npm_packages"] = []

    # pip
    print("  pip...")
    pip_list = run("pip list --format=json 2>/dev/null")
    if pip_list:
        try:
            data["pip_packages"] = [p["name"] for p in json.loads(pip_list)]
        except:
            data["pip_packages"] = []
    else:
        data["pip_packages"] = []

    # Git
    print("  Git...")
    data["git_config"] = {
        "user.name": run("git config --global user.name"),
        "user.email": run("git config --global user.email"),
        "push.default": run("git config --global push.default"),
        "diff.algorithm": run("git config --global diff.algorithm"),
    }
    gitconfig = HOME / ".gitconfig"
    if gitconfig.exists():
        data["gitconfig_raw"] = gitconfig.read_text()

    # SSH
    print("  SSH...")
    ssh_dir = HOME / ".ssh"
    data["ssh_keys"] = []
    if ssh_dir.exists():
        for f in ssh_dir.iterdir():
            if f.suffix == ".pub":
                data["ssh_keys"].append({"name": f.name, "content": f.read_text()})
        ssh_config = ssh_dir / "config"
        if ssh_config.exists():
            data["ssh_config"] = ssh_config.read_text()

    # Docker
    print("  Docker...")
    docker_config = HOME / ".docker" / "config.json"
    if docker_config.exists():
        try:
            data["docker_config"] = json.loads(docker_config.read_text())
        except:
            pass

    # CLI tools
    print("  CLI tools...")
    tools = ["git", "gh", "node", "python3", "ruby", "go", "rust", "cargo",
             "docker", "colima", "kubectl", "flyctl", "heroku", "cloudflared",
             "ngrok", "gemini", "openclaw", "hermes"]
    data["cli_tools"] = {}
    for tool in tools:
        path = run(f"which {tool}")
        if path:
            version = run(f"{tool} --version 2>/dev/null | head -1")
            data["cli_tools"][tool] = {"path": path, "version": version}

    # npmrc
    npmrc = HOME / ".npmrc"
    if npmrc.exists():
        data["npmrc"] = npmrc.read_text()

    return data


def main():
    parser = argparse.ArgumentParser(description="Export workspace config")
    parser.add_argument("-o", "--output", default="workspace-manifest.json")
    parser.add_argument("--self-pack", action="store_true", help="Package self + data into zip")
    args = parser.parse_args()

    print("Exporting workspace config...")
    data = export_workspace()

    out = Path(args.output)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out}")

    # Summary
    print(f"\nSummary:")
    print(f"  Brew: {len(data.get('brew_formulae', []))} formulae, {len(data.get('brew_casks', []))} casks")
    print(f"  npm:  {len(data.get('npm_packages', []))} global packages")
    print(f"  pip:  {len(data.get('pip_packages', []))} packages")
    print(f"  CLI:  {len(data.get('cli_tools', {}))} tools")
    print(f"  SSH:  {len(data.get('ssh_keys', []))} keys")

    if args.self_pack:
        import zipfile
        zip_path = out.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(out, "workspace-manifest.json")
            skill_md = Path(__file__).parent / "SKILL.md"
            if skill_md.exists():
                zf.write(skill_md, "SKILL.md")
        print(f"\nSelf-packed: {zip_path}")


if __name__ == "__main__":
    main()
