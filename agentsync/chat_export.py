"""Conversation export: batch export chat history from all agents."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()


@dataclass
class ChatSession:
    agent: str
    session_id: str
    title: str = ""
    created_at: str = ""
    message_count: int = 0
    file_path: str = ""
    size_bytes: int = 0


# ── Per-agent exporters ────────────────────────────────────

def export_claude_code(output_dir: Path) -> list[ChatSession]:
    """Export Claude Code conversations from ~/.claude/projects/*/."""
    sessions = []
    projects_dir = HOME / ".claude" / "projects"

    if not projects_dir.exists():
        return sessions

    dest = output_dir / "claude-code"
    dest.mkdir(parents=True, exist_ok=True)

    for jsonl_file in sorted(projects_dir.rglob("*.jsonl")):
        project = jsonl_file.parent.name
        session_id = jsonl_file.stem

        # Count messages and get first user message as title
        msg_count = 0
        title = ""
        try:
            for line in jsonl_file.read_text(errors="ignore").splitlines():
                try:
                    d = json.loads(line)
                    if d.get("role") == "user" or d.get("type") == "user":
                        msg_count += 1
                        if not title:
                            content = d.get("content", d.get("message", ""))
                            if isinstance(content, dict):
                                title = str(content.get("content", ""))[:80]
                            elif isinstance(content, str):
                                title = content[:80]
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        title = item.get("text", "")[:80]
                                        break
                except:
                    pass
        except:
            pass

        # Copy file
        project_dir = dest / project
        project_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(jsonl_file, project_dir / jsonl_file.name)

        sessions.append(ChatSession(
            agent="claude-code",
            session_id=session_id,
            title=title,
            message_count=msg_count,
            file_path=str(project_dir / jsonl_file.name),
            size_bytes=jsonl_file.stat().st_size,
        ))

    return sessions


def export_hermes(output_dir: Path) -> list[ChatSession]:
    """Export Hermes sessions via CLI."""
    sessions = []
    dest = output_dir / "hermes"
    dest.mkdir(parents=True, exist_ok=True)

    # Use hermes sessions export
    export_file = dest / "hermes-sessions.jsonl"
    try:
        result = subprocess.run(
            ["hermes", "sessions", "export", str(export_file)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and export_file.exists():
            # Parse exported sessions
            for line in export_file.read_text(errors="ignore").splitlines():
                try:
                    d = json.loads(line)
                    sessions.append(ChatSession(
                        agent="hermes",
                        session_id=d.get("id", ""),
                        title=d.get("title", d.get("preview", ""))[:80],
                        created_at=d.get("created_at", ""),
                    ))
                except:
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Also export state.db if available
    state_db = HOME / ".hermes" / "state.db"
    if state_db.exists():
        shutil.copy2(state_db, dest / "hermes-state.db")

    return sessions


def export_workbuddy(output_dir: Path) -> list[ChatSession]:
    """Export WorkBuddy sessions from SQLite."""
    sessions = []
    dest = output_dir / "workbuddy"
    dest.mkdir(parents=True, exist_ok=True)

    db_path = HOME / ".workbuddy" / "workbuddy.db"
    if not db_path.exists():
        return sessions

    # Export session metadata
    meta_file = dest / "sessions-metadata.jsonl"
    try:
        result = subprocess.run(
            ["sqlite3", str(db_path),
             "SELECT json_object('id', id, 'title', title, 'cwd', cwd, "
             "'created_at', datetime(created_at/1000, 'unixepoch', 'localtime'), "
             "'updated_at', datetime(updated_at/1000, 'unixepoch', 'localtime'), "
             "'model', model) FROM sessions WHERE deleted_at IS NULL ORDER BY updated_at DESC;"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            meta_file.write_text(result.stdout)
            for line in result.stdout.strip().splitlines():
                try:
                    d = json.loads(line)
                    sessions.append(ChatSession(
                        agent="workbuddy",
                        session_id=d.get("id", ""),
                        title=(d.get("title") or "")[:80],
                        created_at=d.get("created_at", ""),
                    ))
                except:
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Export raw JSONL message files
    projects_dir = HOME / ".workbuddy" / "projects"
    if projects_dir.exists():
        raw_dir = dest / "raw_messages"
        raw_dir.mkdir(exist_ok=True)
        count = 0
        for jsonl in projects_dir.rglob("*.jsonl"):
            shutil.copy2(jsonl, raw_dir / jsonl.name)
            count += 1
        if count > 0:
            print(f"    Copied {count} raw message files")

    # Copy database
    shutil.copy2(db_path, dest / "workbuddy.db")

    return sessions


def export_openclaw(output_dir: Path) -> list[ChatSession]:
    """Export OpenClaw sessions."""
    sessions = []
    dest = output_dir / "openclaw"
    dest.mkdir(parents=True, exist_ok=True)

    sessions_dir = HOME / ".openclaw" / "sessions"
    if not sessions_dir.exists():
        return sessions

    for session_file in sorted(sessions_dir.iterdir()):
        if session_file.is_file():
            shutil.copy2(session_file, dest / session_file.name)
            sessions.append(ChatSession(
                agent="openclaw",
                session_id=session_file.name,
                size_bytes=session_file.stat().st_size,
            ))

    return sessions


def export_gemini(output_dir: Path) -> list[ChatSession]:
    """Export Gemini CLI chat sessions."""
    sessions = []
    dest = output_dir / "gemini"
    dest.mkdir(parents=True, exist_ok=True)

    tmp_dir = HOME / ".gemini" / "tmp"
    if not tmp_dir.exists():
        return sessions

    for session_file in sorted(tmp_dir.rglob("*.json")):
        if "session" in session_file.name.lower() or "chat" in session_file.name.lower():
            shutil.copy2(session_file, dest / session_file.name)
            sessions.append(ChatSession(
                agent="gemini",
                session_id=session_file.name,
                size_bytes=session_file.stat().st_size,
            ))

    return sessions


def export_codex(output_dir: Path) -> list[ChatSession]:
    """Export Codex CLI sessions."""
    sessions = []
    dest = output_dir / "codex"
    dest.mkdir(parents=True, exist_ok=True)

    sessions_dir = HOME / ".codex" / "sessions"
    if not sessions_dir.exists():
        return sessions

    for jsonl_file in sorted(sessions_dir.rglob("*.jsonl")):
        msg_count = 0
        title = ""
        try:
            for line in jsonl_file.read_text(errors="ignore").splitlines():
                try:
                    d = json.loads(line)
                    role = d.get("role", "")
                    if role == "user":
                        msg_count += 1
                        if not title:
                            content = d.get("content", "")
                            if isinstance(content, str):
                                title = content[:80]
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        title = item.get("text", "")[:80]
                                        break
                except:
                    pass
        except:
            pass

        dest_file = dest / jsonl_file.name
        shutil.copy2(jsonl_file, dest_file)
        sessions.append(ChatSession(
            agent="codex",
            session_id=jsonl_file.stem,
            title=title,
            message_count=msg_count,
            file_path=str(dest_file),
            size_bytes=jsonl_file.stat().st_size,
        ))

    return sessions


def export_codexia(output_dir: Path) -> list[ChatSession]:
    """Export Codexia sessions."""
    sessions = []
    dest = output_dir / "codexia"
    dest.mkdir(parents=True, exist_ok=True)

    # JSONL sessions
    codexia_dir = HOME / ".codexia"
    if codexia_dir.exists():
        for jsonl in codexia_dir.rglob("*.jsonl"):
            shutil.copy2(jsonl, dest / jsonl.name)
            sessions.append(ChatSession(agent="codexia", session_id=jsonl.stem))

    # SQLite history
    history_db = HOME / ".codexia" / "cache.db"
    if history_db.exists():
        shutil.copy2(history_db, dest / "cache.db")

    return sessions


def export_claude_desktop_3p(output_dir: Path) -> list[ChatSession]:
    """Export Claude Desktop 3p conversations."""
    sessions = []
    dest = output_dir / "claude-desktop-3p"
    dest.mkdir(parents=True, exist_ok=True)

    base = Path.home() / "Library/Application Support/Claude-3p"
    if not base.exists():
        return sessions

    # JSONL files
    for jsonl in base.rglob("*.jsonl"):
        msg_count = 0
        title = ""
        try:
            for line in jsonl.read_text(errors="ignore").splitlines():
                try:
                    d = json.loads(line)
                    if d.get("role") == "user" or d.get("type") == "user":
                        msg_count += 1
                        if not title:
                            c = d.get("content", d.get("message", ""))
                            if isinstance(c, str):
                                title = c[:80]
                            elif isinstance(c, dict):
                                title = str(c.get("content", ""))[:80]
                except:
                    pass
        except:
            pass

        dest_file = dest / jsonl.name
        shutil.copy2(jsonl, dest_file)
        sessions.append(ChatSession(
            agent="claude-desktop-3p",
            session_id=jsonl.stem,
            title=title,
            message_count=msg_count,
            size_bytes=jsonl.stat().st_size,
        ))

    return sessions


def export_autoclaw(output_dir: Path) -> list[ChatSession]:
    """Export AutoClaw sessions from SQLite."""
    sessions = []
    dest = output_dir / "autoclaw"
    dest.mkdir(parents=True, exist_ok=True)

    base = Path.home() / "Library/Application Support/autoclaw"
    for db_file in base.rglob("*.db"):
        if db_file.stat().st_size > 1024:  # Skip tiny dbs
            shutil.copy2(db_file, dest / db_file.name)
            sessions.append(ChatSession(
                agent="autoclaw",
                session_id=db_file.name,
                size_bytes=db_file.stat().st_size,
            ))

    return sessions


def export_atlas(output_dir: Path) -> list[ChatSession]:
    """Export ChatGPT Atlas sessions from SQLite."""
    sessions = []
    dest = output_dir / "chatgpt-atlas"
    dest.mkdir(parents=True, exist_ok=True)

    base = Path.home() / "Library/Application Support/com.openai.atlas"
    for db_file in base.rglob("*.db"):
        if db_file.stat().st_size > 1024:
            shutil.copy2(db_file, dest / db_file.name)
            sessions.append(ChatSession(
                agent="chatgpt-atlas",
                session_id=db_file.name,
                size_bytes=db_file.stat().st_size,
            ))

    return sessions


def export_cherrystudio(output_dir: Path) -> list[ChatSession]:
    """Export CherryStudio sessions."""
    sessions = []
    dest = output_dir / "cherrystudio"
    dest.mkdir(parents=True, exist_ok=True)

    base = Path.home() / "Library/Application Support/CherryStudio"
    for jsonl in base.rglob("*.jsonl"):
        shutil.copy2(jsonl, dest / jsonl.name)
        sessions.append(ChatSession(agent="cherrystudio", session_id=jsonl.stem))

    for db_file in base.rglob("*.db"):
        if db_file.stat().st_size > 1024:
            shutil.copy2(db_file, dest / db_file.name)

    return sessions


def export_anythingllm(output_dir: Path) -> list[ChatSession]:
    """Export AnythingLLM sessions from SQLite."""
    sessions = []
    dest = output_dir / "anythingllm"
    dest.mkdir(parents=True, exist_ok=True)

    base = Path.home() / "Library/Application Support/anythingllm-desktop"
    for db_file in base.rglob("*.db"):
        if db_file.stat().st_size > 1024:
            # Only copy if not too large (> 8GB might be vector DB)
            if db_file.stat().st_size < 500 * 1024 * 1024:  # < 500MB
                shutil.copy2(db_file, dest / db_file.name)
                sessions.append(ChatSession(
                    agent="anythingllm",
                    session_id=db_file.name,
                    size_bytes=db_file.stat().st_size,
                ))
            else:
                sessions.append(ChatSession(
                    agent="anythingllm",
                    session_id=db_file.name,
                    title=f"[SKIPPED - too large: {db_file.stat().st_size / 1024 / 1024:.0f}MB]",
                ))

    return sessions


def export_mavis(output_dir: Path) -> list[ChatSession]:
    """Export Mavis sessions from SQLite."""
    sessions = []
    dest = output_dir / "mavis"
    dest.mkdir(parents=True, exist_ok=True)

    base = HOME / ".mavis"
    for db_file in base.rglob("*.db"):
        if db_file.stat().st_size > 1024:
            if db_file.stat().st_size < 500 * 1024 * 1024:
                shutil.copy2(db_file, dest / db_file.name)
                sessions.append(ChatSession(
                    agent="mavis",
                    session_id=db_file.name,
                    size_bytes=db_file.stat().st_size,
                ))

    return sessions


# ── Main export function ───────────────────────────────────

EXPORTERS = {
    "claude-code": export_claude_code,
    "claude-desktop-3p": export_claude_desktop_3p,
    "hermes": export_hermes,
    "workbuddy": export_workbuddy,
    "openclaw": export_openclaw,
    "gemini": export_gemini,
    "codex": export_codex,
    "codexia": export_codexia,
    "autoclaw": export_autoclaw,
    "chatgpt-atlas": export_atlas,
    "cherrystudio": export_cherrystudio,
    "anythingllm": export_anythingllm,
    "mavis": export_mavis,
}


def export_all_chats(output_dir: Path, agents: list[str] = None) -> dict[str, list[ChatSession]]:
    """Export chat history from all (or specified) agents."""
    if agents is None:
        agents = list(EXPORTERS.keys())

    results = {}
    for agent_name in agents:
        exporter = EXPORTERS.get(agent_name)
        if not exporter:
            print(f"  Unknown agent: {agent_name}")
            continue

        print(f"  Exporting {agent_name}...")
        try:
            sessions = exporter(output_dir)
            results[agent_name] = sessions
            print(f"    {len(sessions)} sessions exported")
        except Exception as e:
            print(f"    Error: {e}")
            results[agent_name] = []

    return results


def generate_index(results: dict[str, list[ChatSession]], output_dir: Path):
    """Generate a human-readable index of all exported chats."""
    index_lines = [
        "# Chat History Export",
        "",
        f"Exported: {datetime.now(timezone.utc).isoformat()}",
        f"Machine: {os.uname().nodename}",
        "",
    ]

    total = sum(len(s) for s in results.values())
    index_lines.append(f"Total: {total} sessions across {len(results)} agents")
    index_lines.append("")

    for agent_name, sessions in results.items():
        index_lines.append(f"## {agent_name} ({len(sessions)} sessions)")
        index_lines.append("")
        for s in sessions[:20]:  # Show first 20
            title = s.title or s.session_id
            size = f" ({s.size_bytes / 1024:.0f}KB)" if s.size_bytes else ""
            index_lines.append(f"- {title}{size}")
        if len(sessions) > 20:
            index_lines.append(f"- ... and {len(sessions) - 20} more")
        index_lines.append("")

    (output_dir / "INDEX.md").write_text("\n".join(index_lines))


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Export chat history from all agents")
    parser.add_argument("-o", "--output", default=None, help="Output directory")
    parser.add_argument("--agents", nargs="*", help="Specific agents to export")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else Path.home() / "Desktop" / "chat-export"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting chat history to: {output_dir}\n")
    results = export_all_chats(output_dir, args.agents)

    generate_index(results, output_dir)

    total = sum(len(s) for s in results.values())
    size = sum(
        sum(s.size_bytes for s in sessions)
        for sessions in results.values()
    )
    print(f"\nTotal: {total} sessions ({size / 1024 / 1024:.1f} MB)")
    print(f"Index: {output_dir / 'INDEX.md'}")


if __name__ == "__main__":
    main()
