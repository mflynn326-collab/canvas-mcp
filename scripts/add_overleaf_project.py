"""Manage the Overleaf projects Claude can see through the Overleaf MCP.

The Overleaf MCP can only reach projects listed in a private projects.json in
the user's config folder (never in this repo). This script adds, lists,
verifies, and removes entries in that file.

    python scripts/add_overleaf_project.py <short-name> <project URL or ID> [--name "Display name"]
    python scripts/add_overleaf_project.py --list
    python scripts/add_overleaf_project.py --verify
    python scripts/add_overleaf_project.py --remove <short-name>
    python scripts/add_overleaf_project.py --reset-token

An Overleaf Git token works for every project in the account, so new entries
reuse the token already in the file and it never has to pass through a chat.
For the very first project there is no token yet: the entry gets a placeholder
the user replaces by editing the file themselves, and --verify then copies the
token into any other entries still holding the placeholder.

The first project added is stored as "default", which Claude uses when a
request doesn't name a project.

The Overleaf MCP reads this file only when the Claude app starts: fully quit
Claude and reopen it after any change.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    PROJECTS_FILE = Path(os.environ["APPDATA"]) / "overleaf-mcp" / "projects.json"
else:
    _config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    PROJECTS_FILE = Path(_config_home) / "overleaf-mcp" / "projects.json"

TOKEN_PLACEHOLDER = "paste-your-overleaf-git-token-here"
RESTART_NOTE = (
    "Fully quit Claude (Windows: Task Manager -> End task on every Claude "
    "process; macOS: Cmd+Q) and reopen it so the Overleaf tools see this change."
)


def load() -> dict:
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text(encoding="utf-8-sig"))
    return {"projects": {}}


def save(data: dict) -> None:
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def has_token(project: dict) -> bool:
    return project.get("gitToken", "").strip() not in ("", TOKEN_PLACEHOLDER)


def account_token(projects: dict) -> str | None:
    for project in projects.values():
        if has_token(project):
            return project["gitToken"].strip()
    return None


def parse_project_id(text: str) -> str:
    """Accept a bare ID or any Overleaf project URL."""
    match = re.search(r"\b[0-9a-f]{24}\b", text.lower())
    if not match:
        sys.exit(
            f"Could not find an Overleaf project ID in {text!r}. It is the "
            "24-character code after /project/ in the project's URL."
        )
    return match.group(0)


def verify(project_id: str, token: str) -> tuple[bool, str]:
    """Check access with `git ls-remote`, the same Git endpoint the MCP uses."""
    url = f"https://git:{token}@git.overleaf.com/{project_id}"
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except FileNotFoundError:
        return False, "git is not installed (the Overleaf MCP needs it too)"
    except subprocess.TimeoutExpired:
        return False, "timed out reaching git.overleaf.com"
    if result.returncode == 0 and result.stdout.strip():
        return True, "OK"
    detail = (result.stderr or result.stdout).replace(token, "***").strip()
    return False, detail.splitlines()[-1] if detail else f"git exited with {result.returncode}"


def cmd_add(key: str, project: str, name: str | None, check: bool) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        sys.exit(f"Short name {key!r} may only use letters, numbers, '-' and '_'.")
    data = load()
    projects = data.setdefault("projects", {})
    project_id = parse_project_id(project)
    stored_key = key if projects else "default"

    for existing_key, existing in projects.items():
        if existing.get("projectId") == project_id:
            sys.exit(f"That project is already listed as {existing_key!r}.")
    if stored_key in projects:
        sys.exit(f"The short name {stored_key!r} is already used; pick another or --remove it first.")

    token = account_token(projects)
    if token and check:
        ok, detail = verify(project_id, token)
        if not ok:
            sys.exit(
                f"Not added: your Overleaf token cannot open project {project_id} ({detail}). "
                "Check the ID, and that your Overleaf account can open this project."
            )
    entry = {"name": name or key, "projectId": project_id, "gitToken": token or TOKEN_PLACEHOLDER}
    projects[stored_key] = entry
    save(data)

    print(f"Added Overleaf project {entry['name']!r} ({project_id}) as {stored_key!r} in {PROJECTS_FILE}")
    if stored_key != key:
        print(
            "It is your first project, so it is saved as 'default': Claude uses it "
            "when a request doesn't name a project."
        )
    if not token:
        print(
            f"\nNo Overleaf Git token yet. Open {PROJECTS_FILE} in a text editor, replace "
            f"{TOKEN_PLACEHOLDER} with your token (Overleaf -> Account Settings -> Git "
            "Integration), save, then run: python scripts/add_overleaf_project.py --verify"
        )
    elif check:
        print("Access verified.")
    print("\n" + RESTART_NOTE)


def cmd_list() -> None:
    projects = load().get("projects", {})
    if not projects:
        print(f"No Overleaf projects yet ({PROJECTS_FILE}).")
        return
    for key, project in projects.items():
        note = "" if has_token(project) else "  [token not set]"
        print(f"{key}: {project.get('name', '')} ({project.get('projectId')}){note}")
    print(f"\nFile: {PROJECTS_FILE}")


def cmd_verify() -> None:
    data = load()
    projects = data.get("projects", {})
    if not projects:
        sys.exit(f"No Overleaf projects in {PROJECTS_FILE} yet.")
    token = account_token(projects)
    if not token:
        sys.exit(
            f"No Overleaf Git token in {PROJECTS_FILE} yet: replace {TOKEN_PLACEHOLDER} "
            "with your token, save, and rerun."
        )

    # Fill placeholders from the account token and strip stray whitespace from pasting.
    changed = []
    for key, project in projects.items():
        cleaned = project["gitToken"].strip() if has_token(project) else token
        if cleaned != project.get("gitToken"):
            project["gitToken"] = cleaned
            changed.append(key)
    if changed:
        save(data)
        print(f"Updated the token in: {', '.join(changed)}")

    failures = 0
    for key, project in projects.items():
        ok, detail = verify(project["projectId"], project["gitToken"])
        failures += not ok
        status = "OK    " if ok else "FAILED"
        suffix = "" if ok else f" -> {detail}"
        print(f"{status}  {key}: {project.get('name', '')} ({project['projectId']}){suffix}")
    if failures:
        sys.exit(1)
    if changed:
        print("\n" + RESTART_NOTE)


def cmd_remove(key: str) -> None:
    data = load()
    if key not in data.get("projects", {}):
        sys.exit(f"No project named {key!r}.")
    del data["projects"][key]
    save(data)
    print(f"Removed {key!r} from {PROJECTS_FILE}\n\n{RESTART_NOTE}")


def cmd_reset_token() -> None:
    """For a revoked/regenerated token: user pastes the new one over any placeholder."""
    data = load()
    projects = data.get("projects", {})
    if not projects:
        sys.exit(f"No Overleaf projects in {PROJECTS_FILE} yet.")
    for project in projects.values():
        project["gitToken"] = TOKEN_PLACEHOLDER
    save(data)
    print(
        f"Cleared the token from every project. Open {PROJECTS_FILE}, paste your new token "
        f"over the first {TOKEN_PLACEHOLDER}, save, then run: "
        "python scripts/add_overleaf_project.py --verify"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the Overleaf projects the Overleaf MCP can see.")
    parser.add_argument("key", nargs="?", help="short name to use in chat, e.g. thesis")
    parser.add_argument("project", nargs="?", help="Overleaf project URL or 24-character ID")
    parser.add_argument("--name", help="display name (defaults to the short name)")
    parser.add_argument("--no-verify", action="store_true", help="skip the access check when adding")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true", help="show configured projects (never the token)")
    action.add_argument("--verify", action="store_true", help="check access to every project")
    action.add_argument("--remove", metavar="SHORT_NAME", help="remove a project")
    action.add_argument("--reset-token", action="store_true", help="clear the token to paste in a new one")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.verify:
        cmd_verify()
    elif args.remove:
        cmd_remove(args.remove)
    elif args.reset_token:
        cmd_reset_token()
    elif args.key and args.project:
        cmd_add(args.key, args.project, args.name, check=not args.no_verify)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
