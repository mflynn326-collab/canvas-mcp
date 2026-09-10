"""Insert the 'overleaf' MCP server entry into Claude Desktop's config.

The server is the open-source @mjyoo2/overleaf-mcp npm package, fetched and
run by npx, pointed at the private projects file that
add_overleaf_project.py manages. Idempotent. Run while the Claude Desktop app
is NOT running, or the app will overwrite the change when it saves its
settings.
"""

import sys

from _desktop_config import upsert_server
from add_overleaf_project import PROJECTS_FILE

if sys.platform == "win32":
    # The desktop app only finds npx on Windows when launched through cmd.
    ENTRY = {"command": "cmd", "args": ["/c", "npx", "-y", "@mjyoo2/overleaf-mcp"]}
else:
    ENTRY = {"command": "npx", "args": ["-y", "@mjyoo2/overleaf-mcp"]}
# Only the projects file: OVERLEAF_PROJECT_ID/OVERLEAF_GIT_TOKEN env vars would
# override it and hide every project but one.
ENTRY["env"] = {"OVERLEAF_PROJECTS_CONFIG": str(PROJECTS_FILE)}

upsert_server("overleaf", ENTRY)
