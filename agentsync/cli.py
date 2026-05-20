"""CLI entry point for onezion-agent-sync."""

from __future__ import annotations

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="onezion-agent-sync",
        description="Unified agent config migration tool — scan, export, import secrets & discover agent configs from docs",
    )
    sub = parser.add_subparsers(dest="command")

    # scan
    sub.add_parser("scan", help="Discover all agents and secrets on this machine")

    # export-secrets
    p_export = sub.add_parser("export-secrets", help="Export all discovered API keys to JSON")
    p_export.add_argument("-o", "--output", help="Output file path", default=None)
    p_export.add_argument("--show-values", action="store_true", help="Print secret values")

    # import
    p_import = sub.add_parser("import", help="Import secrets from a manifest file")
    p_import.add_argument("manifest", help="Path to secrets-export.json")
    p_import.add_argument("--dry-run", action="store_true", help="Preview without writing")

    # docs
    p_docs = sub.add_parser("docs", help="Discover agent config structures from GitHub docs")
    p_docs.add_argument("agent", nargs="?", help="Agent name (e.g. claude-code, hermes)")
    p_docs.add_argument("--all", action="store_true", help="Discover all known agents")
    p_docs.add_argument("--list", action="store_true", help="List all known agents")

    # discover
    sub.add_parser("discover", help="Scan machine for installed agents and their API status")

    # orchestrate
    p_orch = sub.add_parser("orchestrate", help="Auto-export from all agents with APIs, list manual steps")
    p_orch.add_argument("-o", "--output", help="Output directory", default=None)

    # chat-export
    p_chat = sub.add_parser("chat-export", help="Export conversation history from all agents")
    p_chat.add_argument("-o", "--output", help="Output directory", default=None)
    p_chat.add_argument("--agents", nargs="*", help="Specific agents (claude-code, hermes, workbuddy, openclaw, gemini)")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan()
    elif args.command == "export-secrets":
        cmd_export_secrets(args.output, args.show_values)
    elif args.command == "import":
        cmd_import(args.manifest, args.dry_run)
    elif args.command == "docs":
        if args.list:
            cmd_docs_list()
        elif args.all:
            cmd_docs_all()
        elif args.agent:
            cmd_docs_agent(args.agent)
        else:
            cmd_docs_list()
    elif args.command == "discover":
        cmd_discover()
    elif args.command == "orchestrate":
        cmd_orchestrate(args.output)
    elif args.command == "chat-export":
        cmd_chat_export(args.output, args.agents)
    else:
        parser.print_help()


def cmd_scan():
    from .secrets import discover_all
    secrets = discover_all()
    print(f"\nFound {len(secrets)} secrets:\n")
    by_source = {}
    for s in secrets:
        by_source.setdefault(s.source, []).append(s)
    for source, items in sorted(by_source.items()):
        print(f"  [{source}]")
        for s in items:
            agent_tag = f" ({s.agent})" if s.agent else ""
            print(f"    {s.name}{agent_tag}  <-  {s.source_path}")
        print()


def cmd_export_secrets(output, show_values):
    from .secrets import discover_all, export_manifest
    secrets = discover_all()
    out_path = export_manifest(secrets, Path(output) if output else None)
    print(f"Exported {len(secrets)} secrets to {out_path}")
    if show_values:
        print("\n--- Values ---")
        for s in secrets:
            print(f"  {s.name} = {s.value}")
    else:
        print("\nUse --show-values to see actual values.")


def cmd_import(manifest_path, dry_run):
    from .secrets import import_manifest
    path = Path(manifest_path)
    if not path.exists():
        print(f"File not found: {path}")
        return
    actions = import_manifest(path, dry_run=dry_run)
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Import results:\n")
    for action in actions:
        print(f"  {action}")
    print(f"\nTotal: {len(actions)} items processed.")


def cmd_docs_list():
    from .registry import list_agents
    agents = list_agents()
    print(f"\nKnown agents ({len(agents)}):\n")
    for a in agents:
        configs = ", ".join(a.config_paths[:2]) if a.config_paths else "(no known paths)"
        print(f"  {a.name:<20} {a.github:<35} {configs}")
    print()


def cmd_docs_agent(agent_name):
    from .docs import discover_agent
    from pathlib import Path

    cache_dir = Path(__file__).parent.parent / ".cache" / "docs"
    print(f"\nDiscovering {agent_name} from GitHub docs...")
    profile = discover_agent(agent_name, cache_dir=cache_dir)

    print(f"\n  Agent: {profile.name}")
    print(f"  GitHub: {profile.github}")

    if profile.readme_excerpt:
        print(f"\n  README excerpt:")
        for line in profile.readme_excerpt.split("\n")[:5]:
            print(f"    {line.strip()}")

    if profile.config_patterns:
        print(f"\n  Config files found:")
        for p in profile.config_patterns:
            print(f"    {p['path']:<50} ({p['format']}) [{p['source']}]")

    if profile.env_vars:
        print(f"\n  Environment variables:")
        for v in profile.env_vars:
            print(f"    {v}")

    if profile.install_commands:
        print(f"\n  Install commands:")
        for c in profile.install_commands:
            print(f"    {c}")
    print()


def cmd_docs_all():
    from .docs import discover_all_agents
    from pathlib import Path

    cache_dir = Path(__file__).parent.parent / ".cache" / "docs"
    print("\nDiscovering all agents from GitHub docs...\n")
    profiles = discover_all_agents(cache_dir=cache_dir)

    for name, profile in profiles.items():
        pats = len(profile.config_patterns)
        envs = len(profile.env_vars)
        print(f"  {profile.name:<20} {pats} configs, {envs} env vars")
        for p in profile.config_patterns[:3]:
            print(f"    -> {p['path']}")
    print(f"\nCached to {cache_dir}")


def cmd_discover():
    from .orchestrator import discover_installed_agents
    agents = discover_installed_agents()

    installed = [a for a in agents if a.installed]
    not_installed = [a for a in agents if not a.installed]
    with_api = [a for a in installed if a.has_export]
    manual = [a for a in installed if not a.has_export]

    print(f"\nAgent Discovery Report\n")
    print(f"  Installed: {len(installed)}/{len(agents)}")
    print(f"  With API (auto-export): {len(with_api)}")
    print(f"  Manual export needed:   {len(manual)}")
    print()

    if with_api:
        print("  [Auto-exportable]")
        for a in with_api:
            print(f"    {a.name:<20} via {a.api_type}  ({a.export_command})")
        print()

    if manual:
        print("  [Manual export]")
        for a in manual:
            hint = a.manual_hint[:60] if a.manual_hint else ""
            print(f"    {a.name:<20} {hint}")
        print()

    if not_installed:
        print(f"  [Not installed] ({len(not_installed)})")
        for a in not_installed:
            print(f"    {a.name}")
        print()


def cmd_orchestrate(output_dir):
    from .orchestrator import export_all, generate_manual_guide, discover_installed_agents
    from .secrets import discover_all, export_manifest
    from pathlib import Path
    import json

    out = Path(output_dir) if output_dir else Path.home() / "Desktop" / "agent-migration"
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nOrchestrating full export to: {out}\n")

    # 1. Export secrets
    print("1/3 Exporting secrets...")
    secrets = discover_all()
    export_manifest(secrets, out / "secrets-export.json")
    print(f"   Exported {len(secrets)} secrets\n")

    # 2. Discover and export from agents
    print("2/3 Discovering agents...")
    report = export_all(out)

    auto_count = sum(1 for a in report.agents_found if a.get("exported"))
    manual_count = len(report.agents_manual)
    print(f"   Auto-exported: {auto_count} agents")
    print(f"   Manual needed: {manual_count} agents\n")

    # Print results
    for a in report.agents_found:
        if a.get("exported"):
            print(f"   [OK] {a['name']} -> {a.get('export_path', '?')}")
        elif a.get("has_export"):
            print(f"   [FAIL] {a['name']}: {a.get('error', 'unknown error')}")
        else:
            print(f"   [MANUAL] {a['name']}: {a.get('manual_hint', '')[:60]}")

    # 3. Generate manual guide
    if manual_count > 0:
        print(f"\n3/3 Generating manual export guide...")
        guide = generate_manual_guide(
            [a for a in discover_installed_agents() if not a.has_export and a.installed]
        )
        (out / "MANUAL_EXPORT_GUIDE.md").write_text(guide)
        print(f"   Guide: {out / 'MANUAL_EXPORT_GUIDE.md'}")
    else:
        print(f"\n3/3 All agents auto-exported!")

    # Save report
    (out / "discovery-report.json").write_text(report.to_json())
    print(f"\nFull report: {out / 'discovery-report.json'}")
    print(f"Export directory: {out}")


def cmd_chat_export(output, agents):
    from .chat_export import export_all_chats, generate_index
    from pathlib import Path

    out = Path(output) if output else Path.home() / "Desktop" / "chat-export"
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting chat history to: {out}\n")
    results = export_all_chats(out, agents)
    generate_index(results, out)

    total = sum(len(s) for s in results.values())
    size = sum(sum(s.size_bytes for s in sess) for sess in results.values())
    print(f"\nTotal: {total} sessions ({size / 1024 / 1024:.1f} MB)")
    print(f"Index: {out / 'INDEX.md'}")


if __name__ == "__main__":
    main()
