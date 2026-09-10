# Instructions for Claude: setting up this Canvas MCP server

This file is for Claude (Claude Code / the Claude desktop app's Code tab).
When the user asks you to set up the Canvas MCP server, follow these steps in
order. The human-facing overview is in README.md.

## Ground rules

- **Never ask the user to paste their Canvas API token into the chat, and
  never read the token back to them.** The token goes only into the local
  `.env` file, entered by the user themselves.
- Don't commit `.env` or weaken `.gitignore`.
- The server itself is safe-by-default (creates everything unpublished,
  dry-runs syncs), but respect the tool descriptions: confirm with the user
  before announcements, publishes, and deletes.

## Step 1 — Prerequisites

Check for `uv` (`uv --version`). If missing, install it:

- Windows: `winget install astral-sh.uv` (or the PowerShell installer from docs.astral.sh/uv)
- macOS: `brew install uv` or the curl installer

`uv` will provision Python (>=3.11) automatically; a system Python is not required.

## Step 2 — Install dependencies

From this project folder:

```
uv sync
```

## Step 3 — Configure credentials (user does the token part)

1. If `.env` doesn't exist, copy `.env.example` to `.env`.
2. Set `CANVAS_BASE_URL` to the user's Canvas instance (ask if they haven't
   said; Texas State is `https://canvas.txstate.edu`). It's the domain they
   see in the browser when logged into Canvas.
3. Open `.env` for the user (e.g. `notepad .env` on Windows) and ask them to
   replace the placeholder on the `CANVAS_API_TOKEN=` line with the token they
   generated (README Step 1: Canvas → Account → Settings → Approved
   Integrations → + New Access Token), save, and tell you when done.
   **Do not have them paste the token in chat.**

## Step 4 — Verify the connection

```
uv run python scripts/smoke_test.py
```

Expected: the user's name and their teacher/TA courses. On failure, the error
message says whether the token or the base URL is the problem; have the user
fix `.env` and rerun. Do not proceed until this passes.

## Step 5 — Register the server with the Claude app

Preferred, if the `claude` CLI is available (`claude --version` works):

```
claude mcp add --scope user canvas -- uv run --directory <ABSOLUTE_PATH_TO_THIS_FOLDER> python -m canvas_mcp.server
```

Otherwise register in the desktop app's config with the helper script:

```
python scripts/register_canvas.py
```

(or `uv run python scripts/register_canvas.py`). This adds a `canvas` entry to
`claude_desktop_config.json` pointing at this folder's absolute path.

**Known race condition:** the desktop app keeps its config in memory and may
rewrite the file while running or on exit, erasing entries added mid-session.
If you (Claude) run the script from inside a desktop-app session, warn the
user the entry may not survive the next quit. The robust options are:

- the user runs `python scripts/register_canvas.py` themselves in a terminal
  **while the Claude app is fully closed**, or
- on Windows, launch `scripts/watch_and_register.ps1` as a detached background
  process — it waits for the app to exit, then patches the config.

## Step 6 — Tell the user to fully quit and reopen Claude

MCP servers are only loaded at app startup, and closing the Claude window does
not fully quit the app. Tell the user (this matches README Step 4):

- Windows: close the window, open Task Manager (Ctrl+Shift+Esc), end every
  **Claude** process, then reopen Claude.
- macOS: Cmd+Q, then reopen.

## Step 7 — Confirm it works

After the restart, in a fresh session, the user asks: "list my Canvas courses".
If the canvas tools don't appear, check that the `canvas` entry survived in the
config (see the race condition above) and re-register.

## Optional — regression test

`uv run python scripts/regression_test.py <course_id>` runs a live,
self-cleaning test of the tricky Canvas behaviors (folder casing, file
replacement, page HTML round-trip). Only run it against an **unpublished or
sandbox course** the user names, never a live course with students.
