"""MCP server exposing Canvas LMS course-setup tools.

Run with:  python -m canvas_mcp.server   (stdio transport, for Claude Code)

Reads CANVAS_BASE_URL and CANVAS_API_TOKEN from the project's .env file.
All content-creation tools leave things UNPUBLISHED; publishing is explicit.
Targeted delete tools exist (page, file, module item) for repairs — their
descriptions require user confirmation. No grade or enrollment tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server import MCPServer

from . import content, files
from .client import CanvasClient

# .env lives at the project root, two levels above this file (src/canvas_mcp/server.py)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

mcp = MCPServer("canvas")

_client: CanvasClient | None = None


def client() -> CanvasClient:
    global _client
    if _client is None:
        _client = CanvasClient()
    return _client


# -- read-only tools ----------------------------------------------------------


@mcp.tool()
def list_courses() -> list[dict[str, Any]]:
    """List active Canvas courses where the user is a teacher or TA."""
    return content.list_courses(client())


@mcp.tool()
def get_course_structure(course_id: int) -> dict[str, Any]:
    """Get a course's current modules (with items), pages, and assignments.

    Call this before making changes so you know what already exists.
    """
    return content.get_course_structure(client(), course_id)


@mcp.tool()
def list_course_files(course_id: int) -> list[dict[str, Any]]:
    """List all files in a course's Files area with their folder paths (real
    casing, safe to feed back into upload_file), ids, and sizes."""
    file_map = files.canvas_file_map(client(), course_id)
    return [
        {"path": path, "id": f.get("id"), "size": f.get("size"), "url": f.get("url")}
        for path, f in sorted(file_map.items())
    ]


# -- file tools ---------------------------------------------------------------


@mcp.tool()
def upload_file(course_id: int, local_path: str, canvas_folder: str = "") -> dict[str, Any]:
    """Upload one local file to a course's Files area.

    canvas_folder is a path like 'Week 1/Readings' (created if missing, matched
    case-insensitively against existing folders); empty means the Files root.
    An existing file with the same name is replaced; Canvas assigns the
    replacement a NEW file id, so any module items pointing at the old id are
    automatically repointed (reported in 'repointed_module_items').
    """
    result = files.upload_file(client(), course_id, local_path, canvas_folder or None)
    out = {
        "id": result.get("id"),
        "display_name": result.get("display_name"),
        "size": result.get("size"),
        "url": result.get("url"),
    }
    if "replaced_file_id" in result:
        out["replaced_file_id"] = result["replaced_file_id"]
        out["repointed_module_items"] = result["repointed_module_items"]
    return out


@mcp.tool()
def sync_folder(
    course_id: int, local_dir: str, canvas_root: str = "", dry_run: bool = True
) -> dict[str, Any]:
    """Mirror a local folder (recursively) into a course's Files area.

    ALWAYS run with dry_run=True first and show the user the resulting plan
    (files to create / overwrite / skip) before running again with
    dry_run=False. Never deletes anything from Canvas; unchanged files
    (same path and size) are skipped, so re-syncs are cheap.
    canvas_root optionally nests everything under that folder in Canvas.
    """
    return files.sync_folder(client(), course_id, local_dir, canvas_root or None, dry_run)


# -- content tools (everything is created unpublished) ------------------------


@mcp.tool()
def create_module(course_id: int, name: str, position: int = 0) -> dict[str, Any]:
    """Create an (unpublished) module. position is 1-based; 0 appends at the end."""
    result = content.create_module(client(), course_id, name, position or None)
    return {"id": result["id"], "name": result["name"], "position": result.get("position")}


@mcp.tool()
def add_module_item(
    course_id: int,
    module_id: int,
    item_type: str,
    title: str = "",
    content_id: int = 0,
    page_url: str = "",
    external_url: str = "",
) -> dict[str, Any]:
    """Add an item to a module.

    item_type: 'File' (needs content_id from upload_file), 'Page' (needs page_url
    from create_page), 'Assignment' (needs content_id), 'ExternalUrl' (needs
    external_url and title), or 'SubHeader' (needs title only).
    """
    result = content.add_module_item(
        client(),
        course_id,
        module_id,
        item_type,
        title or None,
        content_id or None,
        page_url or None,
        external_url or None,
    )
    return {"id": result["id"], "title": result.get("title"), "type": result.get("type")}


@mcp.tool()
def create_page(course_id: int, title: str, body_html: str) -> dict[str, Any]:
    """Create an (unpublished) content page. body_html must be RAW HTML markup
    (real < > tags, not &lt;-escaped) — convert Markdown/Word content to clean
    HTML before calling. Pre-escaped bodies are rejected."""
    result = content.create_page(client(), course_id, title, body_html)
    return {"page_url": result["url"], "title": result["title"], "html_url": result.get("html_url")}


@mcp.tool()
def get_page(course_id: int, page_url: str) -> dict[str, Any]:
    """Get a page's stored body HTML, title, and published state. Use to verify
    what was written or before editing an existing page."""
    return content.get_page(client(), course_id, page_url)


@mcp.tool()
def update_page(
    course_id: int, page_url: str, body_html: str = "", title: str = ""
) -> dict[str, Any]:
    """Update an existing page's body and/or title. body_html must be RAW HTML;
    empty arguments leave that field unchanged."""
    result = content.update_page(
        client(), course_id, page_url, body_html or None, title or None
    )
    return {"page_url": result["url"], "title": result["title"], "published": result.get("published")}


@mcp.tool()
def delete_page(course_id: int, page_url: str) -> dict[str, Any]:
    """Delete a page. Irreversible — confirm with the user before calling."""
    result = content.delete_page(client(), course_id, page_url)
    return {"deleted": True, "title": result.get("title")}


@mcp.tool()
def create_assignment(
    course_id: int,
    name: str,
    description_html: str = "",
    due_at: str = "",
    points_possible: float = -1,
    submission_types: list[str] | None = None,
) -> dict[str, Any]:
    """Create an (unpublished) assignment.

    due_at is ISO 8601 UTC, e.g. '2026-09-15T05:00:00Z' (11:59 PM the night of
    Sep 14, US Central during daylight time). submission_types options include
    'online_upload', 'online_text_entry', 'online_url', 'on_paper', 'none'.
    points_possible of -1 leaves the Canvas default.
    """
    result = content.create_assignment(
        client(),
        course_id,
        name,
        description_html,
        due_at or None,
        None if points_possible < 0 else points_possible,
        submission_types,
    )
    return {"id": result["id"], "name": result["name"], "html_url": result.get("html_url")}


@mcp.tool()
def update_syllabus(course_id: int, body_html: str) -> dict[str, Any]:
    """Replace the course syllabus body with the given HTML. This overwrites the
    existing syllabus text — confirm with the user if one already exists."""
    result = content.update_syllabus(client(), course_id, body_html)
    return {"course_id": result["id"], "updated": True}


@mcp.tool()
def post_announcement(course_id: int, title: str, message_html: str) -> dict[str, Any]:
    """Post a course announcement. WARNING: this immediately notifies enrolled
    students — always confirm the exact text with the user before calling."""
    result = content.post_announcement(client(), course_id, title, message_html)
    return {"id": result["id"], "title": result["title"], "html_url": result.get("html_url")}


@mcp.tool()
def update_module_item(
    course_id: int,
    module_id: int,
    item_id: int,
    title: str = "",
    position: int = 0,
    indent: int = -1,
    content_id: int = 0,
) -> dict[str, Any]:
    """Update a module item's title, position (1-based), indent, or the
    content_id it points at. Zero/empty/-1 arguments leave that field unchanged.
    To reorder a whole module, prefer reorder_module_items."""
    result = content.update_module_item(
        client(),
        course_id,
        module_id,
        item_id,
        title or None,
        position or None,
        None if indent < 0 else indent,
        content_id or None,
    )
    return {"id": result["id"], "title": result.get("title"), "position": result.get("position")}


@mcp.tool()
def delete_module_item(course_id: int, module_id: int, item_id: int) -> dict[str, Any]:
    """Remove an item from a module (the underlying file/page/assignment is NOT
    deleted). Confirm with the user before calling."""
    content.delete_module_item(client(), course_id, module_id, item_id)
    return {"deleted": True, "item_id": item_id}


@mcp.tool()
def reorder_module_items(course_id: int, module_id: int, item_ids: list[int]) -> list[dict[str, Any]]:
    """Reorder a module's items to match the given list of item ids (all items
    in the module, in the desired final order)."""
    return content.reorder_module_items(client(), course_id, module_id, item_ids)


@mcp.tool()
def delete_file(course_id: int, file_id: int) -> dict[str, Any]:
    """Delete a file from the course. Irreversible, and breaks any module items
    or page links that reference it — confirm with the user before calling."""
    result = content.delete_file(client(), file_id)
    return {"deleted": True, "display_name": result.get("display_name")}


@mcp.tool()
def set_folder_locked(course_id: int, folder_path: str, locked: bool) -> dict[str, Any]:
    """Lock or unlock a Files folder. IMPORTANT: an unpublished module does NOT
    hide the files inside it — students can still reach them by browsing course
    Files. Lock the folder to actually restrict access (use for answer keys,
    quiz copies, instructor-only material)."""
    return content.set_folder_locked(client(), course_id, folder_path, locked)


@mcp.tool()
def publish_module(course_id: int, module_id: int) -> dict[str, Any]:
    """Publish a module, making it visible to students. Note: publishing does
    not lock the files inside — see set_folder_locked for instructor-only
    material."""
    result = content.set_module_published(client(), course_id, module_id, True)
    return {"id": result["id"], "published": result.get("published")}


@mcp.tool()
def unpublish_module(course_id: int, module_id: int) -> dict[str, Any]:
    """Unpublish a module, hiding it from the student module list (files inside
    remain reachable via course Files unless their folder is locked)."""
    result = content.set_module_published(client(), course_id, module_id, False)
    return {"id": result["id"], "published": result.get("published")}


@mcp.tool()
def publish_assignment(course_id: int, assignment_id: int) -> dict[str, Any]:
    """Publish an assignment, making it visible to students."""
    result = content.set_assignment_published(client(), course_id, assignment_id, True)
    return {"id": result["id"], "published": result.get("published")}


@mcp.tool()
def unpublish_assignment(course_id: int, assignment_id: int) -> dict[str, Any]:
    """Unpublish an assignment, hiding it from students."""
    result = content.set_assignment_published(client(), course_id, assignment_id, False)
    return {"id": result["id"], "published": result.get("published")}


if __name__ == "__main__":
    mcp.run()
