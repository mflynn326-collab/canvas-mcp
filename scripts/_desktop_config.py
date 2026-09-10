"""Find Claude Desktop's config file(s) and add an MCP server entry to them.

Shared by the register_*.py scripts. Windows has two builds of the app: the
standard installer reads %APPDATA%\\Claude\\claude_desktop_config.json, while
the Microsoft Store build reads its own copy under
%LOCALAPPDATA%\\Packages\\Claude_*\\LocalCache\\Roaming\\Claude and ignores the
standard file. Entries are written to every config that is present.
"""

import json
import os
import sys
from pathlib import Path

CONFIG_NAME = "claude_desktop_config.json"


def config_paths() -> list:
    if sys.platform == "win32":
        candidates = [Path(os.environ["APPDATA"]) / "Claude" / CONFIG_NAME]
        packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Packages"
        if packages.is_dir():
            candidates += [
                pkg / "LocalCache" / "Roaming" / "Claude" / CONFIG_NAME
                for pkg in packages.glob("Claude_*")
            ]
    else:
        candidates = [Path.home() / "Library" / "Application Support" / "Claude" / CONFIG_NAME]
    present = [p for p in candidates if p.exists() or p.parent.is_dir()]
    return present or candidates[:1]


def upsert_server(name: str, entry: dict) -> None:
    """Add or replace mcpServers[name] in every config; idempotent."""
    for config_file in config_paths():
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8-sig"))
        else:
            config = {}
        servers = config.setdefault("mcpServers", {})
        if servers.get(name) == entry:
            print(f"{name} entry already present in {config_file}")
            continue
        servers[name] = entry
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"{name} entry added to {config_file}")
