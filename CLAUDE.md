# Instructions for Claude: setting up these MCP servers

This file is for Claude (Claude Code / the Claude desktop app's Code tab).
This repo covers two independent setups; do whichever the user asks for:

- **Part A — Canvas:** the MCP server in this repo.
- **Part B — Overleaf:** the open-source `@mjyoo2/overleaf-mcp` npm package,
  plus helper scripts here that manage the user's list of Overleaf projects.

The human-facing overview is in README.md.

## Ground rules

- **Never ask the user to paste a Canvas API token or an Overleaf Git token
  into the chat, and never print either back.** Tokens go only into local
  files, entered by the user themselves: `.env` (Canvas) and the Overleaf
  projects file (outside this repo).
- Don't display the Overleaf projects file (no `cat`/`type`/Read on it) — it
  contains the token. Use `python scripts/add_overleaf_project.py --list`.
- Don't commit `.env` or weaken `.gitignore`.
- The Canvas server is safe-by-default (creates everything unpublished,
  dry-runs syncs), but respect the tool descriptions: confirm with the user
  before announcements, publishes, and deletes.
- Every setup ends with the user **fully quitting Claude and reopening it**
  (see the last section). MCP servers, and the Overleaf project list, are only
  read at app startup.

## Part A — Canvas

### A1 — Prerequisites

Check for `uv` (`uv --version`). If missing, install it:

- Windows: `winget install astral-sh.uv` (or the PowerShell installer from docs.astral.sh/uv)
- macOS: `brew install uv` or the curl installer

`uv` will provision Python (>=3.11) automatically; a system Python is not required.

### A2 — Install dependencies

From this project folder:

```
uv sync
```

### A3 — Configure credentials (user does the token part)

1. If `.env` doesn't exist, copy `.env.example` to `.env`.
2. Set `CANVAS_BASE_URL` to the user's Canvas instance (ask if they haven't
   said; Texas State is `https://canvas.txstate.edu`). It's the domain they
   see in the browser when logged into Canvas.
3. Open `.env` for the user (e.g. `notepad .env` on Windows) and ask them to
   replace the placeholder on the `CANVAS_API_TOKEN=` line with the token they
   generated (README Part 1, Step 1: Canvas → Account → Settings → Approved
   Integrations → + New Access Token), save, and tell you when done.
   **Do not have them paste the token in chat.**

### A4 — Verify the connection

```
uv run python scripts/smoke_test.py
```

Expected: the user's name and their teacher/TA courses. On failure, the error
message says whether the token or the base URL is the problem; have the user
fix `.env` and rerun. Do not proceed until this passes.

### A5 — Register the server with the Claude app

```
uv run python scripts/register_canvas.py
```

This adds a `canvas` entry, pointing at this folder's absolute path, to every
Claude Desktop config present (the standard and Microsoft Store builds of the
app keep separate files). The desktop app's chats, Cowork, and the Code tab
all read it. If the user also runs the `claude` CLI in a terminal, additionally:
`claude mcp add --scope user canvas -- uv run --directory <ABSOLUTE_PATH_TO_THIS_FOLDER> python -m canvas_mcp.server`.

**Known race condition:** the desktop app keeps its config in memory and may
rewrite the file while running or on exit, erasing entries added mid-session.
If you (Claude) run the script from inside a desktop-app session, warn the
user the entry may not survive the next quit. The robust options are:

- the user runs `python scripts/register_canvas.py` themselves in a terminal
  **while the Claude app is fully closed**, or
- on Windows, launch `scripts/watch_and_register.ps1` as a detached background
  process — it waits for the app to exit, then patches the config. Pass
  `-Servers canvas,overleaf` to re-register both.

### A6 — Fully quit and reopen, then confirm

Tell the user to fully quit and reopen Claude (last section). After the
restart, in a fresh chat, the user asks: "list my Canvas courses". If the
canvas tools don't appear, check that the `canvas` entry survived in the
config (see the race condition above) and re-register.

### Optional — regression test

`uv run python scripts/regression_test.py <course_id>` runs a live,
self-cleaning test of the tricky Canvas behaviors (folder casing, file
replacement, page HTML round-trip). Only run it against an **unpublished or
sandbox course** the user names, never a live course with students.

## Part B — Overleaf

The Overleaf MCP lets Claude list, read, and edit files in the user's Overleaf
projects; edits are pushed to Overleaf as Git commits. It can only reach
projects listed in the user's private projects file:

- Windows: `%APPDATA%\overleaf-mcp\projects.json`
- macOS/Linux: `~/.config/overleaf-mcp/projects.json`

`scripts/add_overleaf_project.py` manages that file. It uses only the standard
library, so run it with `python` or `uv run python`.

### B1 — Check the user's Overleaf plan

The server uses Overleaf's Git integration, which usually needs a paid or
institutional Overleaf plan. Ask the user to confirm they see **Git
Integration** under Overleaf → Account Settings. If they don't, stop and
explain that their plan doesn't include it.

### B2 — Prerequisites

- **Node.js 18+** (`node --version`). Windows: `winget install OpenJS.NodeJS.LTS`;
  macOS: `brew install node`.
- **Git** (`git --version`). Windows: `winget install Git.Git`; macOS:
  `xcode-select --install` or `brew install git`. The server runs git for
  every read and write.
- **Python 3.8+ or uv** to run the helper scripts.

After a winget install the current shell's PATH is stale: confirm the install
in a new shell, or by full path (`C:\Program Files\nodejs\node.exe`,
`C:\Program Files\Git\cmd\git.exe`).

### B3 — Add the first project

Get the project's URL (or its 24-character ID) and a short name for it
(letters, numbers, `-`, `_`; e.g. `thesis`) from the user, then run:

```
python scripts/add_overleaf_project.py thesis "https://www.overleaf.com/project/<ID>" --name "Thesis draft"
```

The first project is stored under the key `default` (display name keeps the
user's name), which the tools use when no project is named. There is no token
yet, so the entry gets a placeholder. Open the file path the script printed
for the user (Windows: `notepad "<path>"`; macOS: `open -e "<path>"`) and ask
them to:

1. create a token in Overleaf → Account Settings → Git Integration,
2. paste it over `paste-your-overleaf-git-token-here`, keeping the quotes,
3. save and tell you when done.

**Do not have them paste the token in chat.**

### B4 — Verify

```
python scripts/add_overleaf_project.py --verify
```

Every project must show `OK`. `FAILED` with an authentication error means the
token was pasted incorrectly (lost quotes, extra characters) or can't open the
project; have the user fix the file and rerun. Don't continue until it passes.

### B5 — Register the server

```
python scripts/register_overleaf.py
```

Adds an `overleaf` entry (npx `@mjyoo2/overleaf-mcp` with
`OVERLEAF_PROJECTS_CONFIG` pointing at the projects file) to every Claude
Desktop config present. The race condition from A5 applies here too; the
watcher takes `-Servers overleaf` or `-Servers canvas,overleaf`.

Don't add `OVERLEAF_PROJECT_ID` / `OVERLEAF_GIT_TOKEN` env vars to the entry:
they override the projects file and would hide every other project.

### B6 — Fully quit and reopen, then confirm

Tell the user to fully quit and reopen Claude (last section). After the
restart, in a new chat, the user asks "list my Overleaf projects" (the
`list_projects` tool); every project should appear.

### Managing projects later

When the user asks to add an Overleaf project (URL or ID, plus a short name):

```
python scripts/add_overleaf_project.py <short-name> "<URL or ID>" [--name "Display name"]
```

The script reuses the token already in the file (Overleaf tokens are
account-wide), checks access with `git ls-remote`, and refuses to add a project
the token can't open. If the user gives no short name, ask for one. Other
commands:

- `--list` — show projects (never the token)
- `--verify` — check access to every project
- `--remove <short-name>`
- `--reset-token` — for a regenerated/revoked token: clears the token from
  every entry; open the projects file for the user to paste the new token over
  the first placeholder, then run `--verify`, which copies it into every entry
  and checks access.

After any add, remove, or token change, tell the user to fully quit and reopen
Claude: the running server read the project list at startup and won't see the
change until then. "Claude only finds `default`" right after adding a project
means Claude wasn't fully quit.

If a user pastes an Overleaf project link into a chat and asks Claude to edit
it, explain that the project has to be added first (this folder, Code tab),
followed by a restart; the server can't reach projects that aren't in its list.

### Using the Overleaf tools

Tools take an optional `projectName` (the short name; default `default`).
Call `list_projects` when unsure which project the user means. `write_file`
and `write_section` commit and push to Overleaf immediately, so show the user
the change and get a yes before writing. A push can fail if the user is
editing the same file in the browser at that moment; re-read and retry.

## Fully quit and reopen Claude

MCP servers (and the Overleaf project list) are only loaded at app startup,
and closing the Claude window does not fully quit the app. Tell the user
(this matches the README):

- Windows: close the window, open Task Manager (Ctrl+Shift+Esc), end every
  **Claude** process, then reopen Claude.
- macOS: Cmd+Q, then reopen.
