# canvas-mcp

An MCP server that lets Claude manage your Canvas LMS courses — uploading files,
syncing local folders into course Files, and building modules, pages,
assignments, and the syllabus — through the Canvas REST API.

Built and battle-tested at Texas State (`canvas.txstate.edu`), but it works with
any Canvas instance: just set your school's Canvas URL during setup.

**You do not need to know how to code to use this.** Claude does the
installation for you (instructions for it are in [CLAUDE.md](CLAUDE.md)), and
afterwards you manage your courses by talking to Claude in plain English.

---

## Setup

### Step 1 — Get a Canvas API token

The token is what lets Claude act on Canvas as you. It is self-service; no
admin or IT ticket needed:

1. Log into Canvas in your browser (Texas State: [canvas.txstate.edu](https://canvas.txstate.edu)).
2. Click **Account** (left sidebar) → **Settings**.
3. Scroll down to **Approved Integrations** and click **+ New Access Token**.
4. Purpose: something like "Claude MCP". Optionally set an expiration date
   (you can always generate a new token later).
5. Click **Generate Token** and **copy the token now** — Canvas only shows it
   once.

**Treat this token like your Canvas password.** It carries your full instructor
permissions. Do not paste it into a chat with Claude, an email, or a shared
document. During setup you will paste it into a private local file called
`.env` that never leaves your computer, and Claude is instructed never to ask
you for it directly. You can revoke the token at any time from the same
Approved Integrations page.

### Step 2 — Download this project

Either click **Code → Download ZIP** on GitHub and unzip it somewhere permanent
(e.g. `Documents\canvas-mcp` — not your Downloads folder), or clone it:

```bash
git clone https://github.com/<this-repo> canvas-mcp
```

The folder must stay where you put it — Claude registers its exact location.

### Step 3 — Let Claude set it up

1. Open the **Claude desktop app**, go to the **Code** tab, and open the
   `canvas-mcp` folder you just unzipped.
2. Send this prompt:

   > Please read CLAUDE.md and set up the Canvas MCP server for me. My Canvas
   > URL is https://canvas.txstate.edu

   (swap in your school's Canvas URL if different)
3. Claude will install what's needed, then pause and ask you to paste your
   token into the `.env` file it opens for you. Do that, save the file, and
   tell Claude you're done. It will verify the connection by listing your
   courses and register the server with the Claude app.

### Step 4 — Fully quit Claude and reopen (required)

The Claude app only loads MCP servers when it starts, and closing the window
does **not** fully quit it. To actually restart it on Windows:

1. Close the Claude window.
2. Press **Ctrl+Shift+Esc** to open Task Manager.
3. Find every **Claude** process, right-click → **End task**.
4. Reopen Claude.

(macOS: Cmd+Q fully quits; then reopen.)

### Step 5 — Try it

In a new Claude session, ask:

> List my Canvas courses

If you get your course list back, you're done. From there, things like:

- "Dry-run a sync of `C:\Courses\FIN3312\Fall2026` into my FIN 3312 course"
- "Create a 'Week 1' module with the syllabus page and these two readings"
- "Create an assignment 'Reaction Paper 1', 20 points, online upload, due Sept 15 at 11:59 PM"
- "Lock the Instructor Only folder so students can't see it"

---

## What Claude can do with it (23 tools)

Listing courses, course structure, and files; uploading files and syncing whole
local folders (dry-run first, never deletes); creating and editing modules,
module items, pages, and assignments; setting the syllabus; posting
announcements; publishing/unpublishing; locking folders; and targeted deletes
(page, file, module item) for repairs.

## Safety design

- Everything is created **unpublished**; publishing is a separate explicit step.
- `sync_folder` defaults to **dry-run** and never deletes anything from Canvas.
- Posting an announcement is the only action that immediately notifies
  students, and Claude is instructed to confirm the text with you first.
- Delete tools are limited to single pages/files/module items and require your
  confirmation. There are **no grading or enrollment tools**.
- **Unpublished modules do not hide files** — students can browse course Files
  directly. Ask Claude to lock the folder for answer keys and instructor-only
  material.

## Canvas quirks this server handles for you

- Canvas folder names are **case sensitive** ('Week 01' ≠ 'week 01'); the
  server matches folders case-insensitively and reuses what exists, so you
  never get duplicate folder trees.
- Replacing a file gives it a **new internal id**, which silently breaks module
  links in stock Canvas; the server automatically repoints affected module
  items and reports what it fixed.

## Troubleshooting

- **Canvas tools missing after restart:** the Claude app occasionally rewrites
  its config and drops manually-added servers. Fully quit Claude (Step 4),
  run `python scripts/register_canvas.py` from a terminal, then reopen. Ask
  Claude about `scripts/watch_and_register.ps1` if it keeps happening.
- **"CANVAS_API_TOKEN is not set"** or authentication errors: re-check `.env` —
  the token must be on the `CANVAS_API_TOKEN=` line with no quotes or spaces,
  and your Canvas URL on the `CANVAS_BASE_URL=` line.
- **Verify the connection any time:** `uv run python scripts/smoke_test.py`
  from the project folder.

## Layout

- `src/canvas_mcp/server.py` — MCP tool definitions
- `src/canvas_mcp/client.py` — auth, pagination, rate-limit backoff, error handling
- `src/canvas_mcp/files.py` — Canvas 3-step file upload, folder-case resolution, sync
- `src/canvas_mcp/content.py` — modules, pages, assignments, syllabus, announcements
- `scripts/` — smoke test, config registration helpers, live regression test
  (`regression_test.py <course_id>` — point it at an **unpublished** course only)
