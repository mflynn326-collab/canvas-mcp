"""Insert the 'canvas' MCP server entry into Claude Desktop's config.

Idempotent: does nothing if the entry already exists. Run while the
Claude Desktop app is NOT running, or the app will overwrite the change
when it saves its settings.
"""

from pathlib import Path

from _desktop_config import upsert_server

PROJECT_DIR = Path(__file__).resolve().parents[1]

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

upsert_server("canvas", ENTRY)
