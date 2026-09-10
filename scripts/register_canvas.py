"""Insert the 'canvas' MCP server entry into Claude Desktop's config.

Idempotent: does nothing if the entry already exists. Run while the
Claude Desktop app is NOT running, or the app will overwrite the change
when it saves its settings.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

if sys.platform == "win32":
    CONFIG = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
else:
    CONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"

ENTRY = {
    "command": "uv",
    "args": [
        "run",
        "--directory",
        str(PROJECT_DIR),
        "python",
        "-m",
        "canvas_mcp.server",
    ],
}

if CONFIG.exists():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
else:
    config = {}

servers = config.setdefault("mcpServers", {})
if servers.get("canvas") == ENTRY:
    print("canvas entry already present; nothing to do")
else:
    servers["canvas"] = ENTRY
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"canvas entry added to {CONFIG}")
