"""Canvas file uploads and local-folder -> course Files syncing.

Canvas uploads are a 3-step dance:
  1. POST the file's metadata to Canvas, which returns a one-time upload URL.
  2. POST the actual bytes (multipart) to that URL, WITHOUT the auth header.
  3. Follow the confirmation redirect (with auth) to finalize and get the File object.

Two Canvas behaviors this module compensates for:
  - Folder names are case sensitive, so 'Week 01' and 'week 01' are different
    folders. We resolve the target folder case-insensitively against existing
    folders and reuse the exact casing that is already there.
  - on_duplicate=overwrite replaces the file but assigns a NEW file id
    (verified empirically), which silently breaks module items that reference
    the old id. After a replacing upload we repoint those module items.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .client import CanvasAPIError, CanvasClient


def _course_folders(client: CanvasClient, course_id: int) -> dict[int, str]:
    """folder_id -> relative path ('' for the Files root), real casing preserved."""
    out: dict[int, str] = {}
    for f in client.get_paginated(f"/courses/{course_id}/folders"):
        out[f["id"]] = f["full_name"].removeprefix("course files").lstrip("/")
    return out


def _resolve_folder(client: CanvasClient, course_id: int, canvas_folder: str | None) -> str | None:
    """Match the requested folder against existing folders case-insensitively.

    Returns the existing folder's exact (real-cased) path if one matches, else
    the caller's path unchanged (Canvas will create it).
    """
    if not canvas_folder:
        return None
    wanted = canvas_folder.strip("/")
    for real in _course_folders(client, course_id).values():
        if real.lower() == wanted.lower():
            return real
    return wanted


def _find_file_in_folder(
    client: CanvasClient, course_id: int, folder: str | None, name: str
) -> dict[str, Any] | None:
    """The existing File object at folder/name, if any (case-insensitive match)."""
    folders = _course_folders(client, course_id)
    target = (folder or "").strip("/").lower()
    for f in client.get_paginated(f"/courses/{course_id}/files", {"search_term": name}):
        if (
            f["display_name"].lower() == name.lower()
            and folders.get(f["folder_id"], "").lower() == target
        ):
            return f
    return None


def _repoint_module_items(
    client: CanvasClient, course_id: int, old_file_id: int, new_file_id: int
) -> list[dict[str, Any]]:
    """Update every File module item pointing at old_file_id to new_file_id."""
    repointed = []
    for module in client.get_paginated(f"/courses/{course_id}/modules", {"include[]": ["items"]}):
        items = module.get("items")
        if items is None:
            items = client.get_paginated(f"/courses/{course_id}/modules/{module['id']}/items")
        for item in items:
            if item.get("type") == "File" and item.get("content_id") == old_file_id:
                client.put(
                    f"/courses/{course_id}/modules/{module['id']}/items/{item['id']}",
                    {"module_item": {"content_id": new_file_id}},
                )
                repointed.append({"module": module["name"], "item": item.get("title")})
    return repointed


def upload_file(
    client: CanvasClient,
    course_id: int,
    local_path: str,
    canvas_folder: str | None = None,
    on_duplicate: str = "overwrite",
) -> dict[str, Any]:
    """Upload one local file into a course's Files area.

    Returns the Canvas File object plus, when the upload replaced an existing
    file, 'replaced_file_id' and the list of 'repointed_module_items'.
    """
    path = Path(local_path)
    if not path.is_file():
        raise CanvasAPIError(0, f"Local file not found: {local_path}", "")

    folder = _resolve_folder(client, course_id, canvas_folder)
    existing = _find_file_in_folder(client, course_id, folder, path.name)

    # Step 1: declare the upload
    declare: dict[str, Any] = {
        "name": path.name,
        "size": path.stat().st_size,
        "on_duplicate": on_duplicate,
    }
    if folder:
        declare["parent_folder_path"] = folder
    ticket = client.post(f"/courses/{course_id}/files", declare)

    upload_url = ticket["upload_url"]
    upload_params = ticket.get("upload_params", {})

    # Step 2: send the bytes. This request must NOT carry our bearer token, and the
    # file field must come last in the multipart body, so use a fresh plain client.
    with httpx.Client(timeout=300.0, follow_redirects=False) as plain:
        with path.open("rb") as fh:
            response = plain.post(upload_url, data=upload_params, files={"file": (path.name, fh)})

        # Step 3: finalize. Either a redirect we must follow with auth, or a 201 with the file JSON.
        if response.status_code in (301, 302, 303):
            # httpx accepts the absolute confirmation URL directly
            result = client.get(response.headers["location"])
        elif response.status_code >= 400:
            raise CanvasAPIError(response.status_code, response.text[:500], upload_url)
        else:
            result = response.json()

    # Canvas's overwrite assigns a new id; keep module links working ourselves.
    if existing and result.get("id") != existing["id"]:
        result["replaced_file_id"] = existing["id"]
        result["repointed_module_items"] = _repoint_module_items(
            client, course_id, existing["id"], result["id"]
        )
    return result


def canvas_file_map(client: CanvasClient, course_id: int) -> dict[str, dict[str, Any]]:
    """Map of 'Relative/Folder/name.ext' -> Canvas File object, real casing preserved."""
    folders = _course_folders(client, course_id)
    file_map: dict[str, dict[str, Any]] = {}
    for f in client.get_paginated(f"/courses/{course_id}/files"):
        rel_dir = folders.get(f["folder_id"], "")
        rel_path = f"{rel_dir}/{f['display_name']}" if rel_dir else f["display_name"]
        file_map[rel_path] = f
    return file_map


def sync_folder(
    client: CanvasClient,
    course_id: int,
    local_dir: str,
    canvas_root: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Mirror a local folder into a course's Files area.

    Compares each local file against what's already in Canvas (by path + size,
    case-insensitively): missing files are uploaded, same-path-different-size
    files are overwritten (module items repointed as needed), same-size files
    are skipped. Nothing is ever deleted from Canvas.

    With dry_run=True (the default) returns the plan without uploading anything.
    """
    root = Path(local_dir)
    if not root.is_dir():
        raise CanvasAPIError(0, f"Local folder not found: {local_dir}", "")

    existing = {path.lower(): obj for path, obj in canvas_file_map(client, course_id).items()}
    prefix = canvas_root.strip("/") if canvas_root else ""

    to_create: list[dict[str, Any]] = []
    to_overwrite: list[dict[str, Any]] = []
    skipped: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        canvas_path = f"{prefix}/{rel}" if prefix else rel
        entry = {
            "local_path": str(path),
            "canvas_path": canvas_path,
            "size": path.stat().st_size,
        }
        current = existing.get(canvas_path.lower())
        if current is None:
            to_create.append(entry)
        elif current.get("size") != entry["size"]:
            to_overwrite.append(entry)
        else:
            skipped.append(canvas_path)

    plan = {
        "dry_run": dry_run,
        "create": to_create,
        "overwrite": to_overwrite,
        "skipped_unchanged": skipped,
    }
    if dry_run:
        return plan

    uploaded = []
    for entry in to_create + to_overwrite:
        folder = str(Path(entry["canvas_path"]).parent.as_posix())
        folder = "" if folder == "." else folder
        result = upload_file(client, course_id, entry["local_path"], folder or None)
        info = {"canvas_path": entry["canvas_path"], "url": result.get("url", "")}
        if "repointed_module_items" in result:
            info["repointed_module_items"] = result["repointed_module_items"]
        uploaded.append(info)
    plan["uploaded"] = uploaded
    return plan
