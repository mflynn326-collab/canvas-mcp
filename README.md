# canvas-mcp

Let Claude work directly in your **Canvas LMS courses** and your **Overleaf
LaTeX projects** — you just ask in plain English.

- **Canvas** (the MCP server in this repo): upload files, sync local folders
  into course Files, and build modules, pages, assignments, and the syllabus
  through the Canvas REST API.
- **Overleaf** (optional): a guided setup for the open-source
  [Overleaf MCP](https://www.npmjs.com/package/@mjyoo2/overleaf-mcp), so
  Claude can read your papers, pull out sections, and write edits back to
  Overleaf.

Set up either one or both. Built and battle-tested at Texas State
(`canvas.txstate.edu`), but it works with any Canvas instance.

**You do not need to know how to code to use this.** Claude does the
installation for you (its instructions are in [CLAUDE.md](CLAUDE.md)), and
afterwards you just talk to Claude.

---

## Before you start: download this project

Either click **Code → Download ZIP** on
[github.com/mflynn326-collab/canvas-mcp](https://github.com/mflynn326-collab/canvas-mcp)
and unzip it somewhere permanent (e.g. `Documents\canvas-mcp` — not your
Downloads folder), or clone it:

```bash
git clone https://github.com/mflynn326-collab/canvas-mcp
```

The folder must stay where you put it: Claude registers its exact location,
and the helper scripts Claude uses later live here.

All the setup below happens in the **Claude desktop app → Code tab**, with this
`canvas-mcp` folder open (use the folder picker to choose it).

---

## Part 1 — Canvas

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

### Step 2 — Let Claude set it up

With the `canvas-mcp` folder open in the Code tab, send:

> Please read CLAUDE.md and set up the Canvas MCP server for me. My Canvas
> URL is https://canvas.txstate.edu

(swap in your school's Canvas URL if different)

Claude will install what's needed, then pause and ask you to paste your token
into the `.env` file it opens for you. Do that, save the file, and tell Claude
you're done. It will verify the connection by listing your courses and
register the server with the Claude app.

### Step 3 — Fully quit Claude and reopen it

Required — see [Fully quit and reopen Claude](#fully-quit-and-reopen-claude-required)
below. Closing the window is not enough.

### Step 4 — Try it

In a new Claude chat, ask:

> List my Canvas courses

If you get your course list back, you're done. From there, things like:

- "Dry-run a sync of `C:\Courses\FIN3312\Fall2026` into my FIN 3312 course"
- "Create a 'Week 1' module with the syllabus page and these two readings"
- "Create an assignment 'Reaction Paper 1', 20 points, online upload, due Sept 15 at 11:59 PM"
- "Lock the Instructor Only folder so students can't see it"

---

## Part 2 — Overleaf (optional)

Once connected, Claude can list the files in your Overleaf projects, read them,
show a paper's section outline, pull out a single section, and write changes
back — every edit is saved to Overleaf and shows up in the project's History.

### What you need

1. **Overleaf Git integration.** It usually requires a paid Overleaf plan or a
   university license. Check: Overleaf → **Account Settings** → look for
   **Git Integration**. If it isn't there, your plan doesn't include it and
   this part won't work.
2. **An Overleaf Git token.** In Account Settings → Git Integration, create a
   token. One token covers every project in your account. Treat it like a
   password: don't paste it into a chat. Claude will open a private file for
   you to paste it into.
3. **The link to one of your Overleaf projects** — copy the address from your
   browser while the project is open (`https://www.overleaf.com/project/...`).

Claude installs the remaining prerequisites (Node.js and Git) if they're missing.

### Step 1 — Ask Claude to set it up

With the `canvas-mcp` folder open in the Code tab, send (with your own link and
a short name for the project):

> Please read CLAUDE.md and set up the Overleaf MCP for me. My first project
> is https://www.overleaf.com/project/PASTE-ID-HERE and I'd like to call it
> "thesis".

Claude will:

- install Node.js and Git if needed,
- create your private project list — on Windows
  `%APPDATA%\overleaf-mcp\projects.json`, outside this folder, so it is never
  shared or uploaded,
- open that file in Notepad and ask you to paste your Git token over the
  placeholder — do that, save, and tell Claude you're done,
- check it can reach your project, and register the Overleaf server with the
  Claude app.

### Step 2 — Fully quit Claude and reopen it

Required — see [Fully quit and reopen Claude](#fully-quit-and-reopen-claude-required).

### Step 3 — Try it

In a new chat:

> List my Overleaf projects

Then things like:

- "Show me the section outline of main.tex in my thesis project"
- "Read the introduction of main.tex in thesis and suggest tighter wording — show me before changing anything"
- "Replace the abstract in thesis with this version: ..."

### Adding more Overleaf projects

Claude can't browse your Overleaf account. It can only see the projects in your
local project list, so **each project is added once**; after that it's
available in every chat.

To add one, open the `canvas-mcp` folder in the Code tab and ask:

> Add my Overleaf project https://www.overleaf.com/project/PASTE-ID-HERE as "crypto"

Claude runs a helper script that reuses the token you already saved (you never
paste it again), checks it can open the project, and adds it. **Then fully
quit and reopen Claude** — the Overleaf server reads its project list only
when Claude starts, so a new project won't show up until you do. After that,
in any chat: *"In my crypto project, list the files."*

Other things you can ask (with the `canvas-mcp` folder open):

- "Which Overleaf projects do I have set up?"
- "Check that all my Overleaf projects still connect"
- "Remove the crypto Overleaf project"
- "I have a new Overleaf token" (after regenerating or revoking the old one)

> **Why can't I just paste a project link into a chat?** The Overleaf server
> only knows the projects in your list, which is where each project is paired
> with your token, and it reads that list once when Claude starts. A link
> pasted into a regular chat gives it nothing it can use. Add the project once
> (above), restart Claude, and from then on just refer to it by its name.

### Good to know

- Your **first project becomes the default**: Claude uses it when you don't
  name a project.
- Edits Claude makes are saved straight to Overleaf as commits by
  "Overleaf MCP". The project's **History** in Overleaf shows each one and lets
  you roll back. Asking Claude to show you a change before writing it is a good
  habit.
- Your token lives only in your private project list, never in this folder or
  on GitHub.

---

## Fully quit and reopen Claude (required)

The Claude app only loads its connections (MCP servers), and the Overleaf
project list, when it starts, and **closing the window does not fully quit
it**. Do this after setting up Canvas, after setting up Overleaf, and after
every time you add or remove an Overleaf project:

1. Close the Claude window.
2. Press **Ctrl+Shift+Esc** to open **Task Manager**.
3. Find every **Claude** process (there are usually several), right-click
   each → **End task**.
4. Reopen Claude.

(macOS: **Cmd+Q** fully quits; then reopen.)

The new tools appear in your next chat.

---

## What Claude can do with Canvas (23 tools)

Listing courses, course structure, and files; uploading files and syncing whole
local folders (dry-run first, never deletes); creating and editing modules,
module items, pages, and assignments; setting the syllabus; posting
announcements; publishing/unpublishing; locking folders; and targeted deletes
(page, file, module item) for repairs.

## Canvas safety design

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

- **A new Overleaf project doesn't show up / Claude only finds "default":**
  Claude wasn't fully quit. End every Claude process in Task Manager and
  reopen (see above).
- **Canvas or Overleaf tools missing after a restart:** the Claude app
  occasionally rewrites its config and drops manually-added servers. Fully
  quit Claude, run `python scripts/register_canvas.py` and/or
  `python scripts/register_overleaf.py` from a terminal, then reopen. Ask
  Claude about `scripts/watch_and_register.ps1` if it keeps happening.
- **"CANVAS_API_TOKEN is not set"** or Canvas authentication errors: re-check
  `.env` — the token must be on the `CANVAS_API_TOKEN=` line with no quotes or
  spaces, and your Canvas URL on the `CANVAS_BASE_URL=` line.
- **Overleaf "authentication failed":** the token was revoked or expired. Ask
  Claude "I have a new Overleaf token" (with the `canvas-mcp` folder open).
- **Verify the connections any time**, from the project folder:
  `uv run python scripts/smoke_test.py` (Canvas) and
  `python scripts/add_overleaf_project.py --verify` (Overleaf).

## Layout

- `src/canvas_mcp/server.py` — MCP tool definitions
- `src/canvas_mcp/client.py` — auth, pagination, rate-limit backoff, error handling
- `src/canvas_mcp/files.py` — Canvas 3-step file upload, folder-case resolution, sync
- `src/canvas_mcp/content.py` — modules, pages, assignments, syllabus, announcements
- `scripts/add_overleaf_project.py` — add, list, verify, and remove Overleaf
  projects (reuses your saved token)
- `scripts/register_canvas.py`, `scripts/register_overleaf.py` — add the
  servers to the Claude app's config (standard and Microsoft Store installs)
- `scripts/` also has the Canvas smoke test and a live regression test
  (`regression_test.py <course_id>` — point it at an **unpublished** course only)
