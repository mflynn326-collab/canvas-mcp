"""Course content operations: modules, pages, assignments, syllabus, announcements."""

from __future__ import annotations

from typing import Any

from .client import CanvasAPIError, CanvasClient


def list_courses(client: CanvasClient) -> list[dict[str, Any]]:
    """Active courses where the user is a teacher or TA."""
    courses: list[dict[str, Any]] = []
    seen: set[int] = set()
    for role in ("teacher", "ta"):
        for c in client.get_paginated(
            "/courses",
            {"enrollment_type": role, "state[]": ["unpublished", "available"], "include[]": ["term"]},
        ):
            if c["id"] not in seen:
                seen.add(c["id"])
                courses.append(
                    {
                        "id": c["id"],
                        "name": c.get("name"),
                        "course_code": c.get("course_code"),
                        "term": (c.get("term") or {}).get("name"),
                        "workflow_state": c.get("workflow_state"),
                    }
                )
    return courses


def get_course_structure(client: CanvasClient, course_id: int) -> dict[str, Any]:
    """Modules (with items), pages, and assignments for one course."""
    modules = []
    for m in client.get_paginated(f"/courses/{course_id}/modules", {"include[]": ["items"]}):
        items = m.get("items")
        if items is None:  # Canvas omits items for very large modules
            items = list(client.get_paginated(f"/courses/{course_id}/modules/{m['id']}/items"))
        modules.append(
            {
                "id": m["id"],
                "name": m["name"],
                "position": m.get("position"),
                "published": m.get("published"),
                "items": [
                    {
                        "id": i["id"],
                        "title": i.get("title"),
                        "type": i.get("type"),
                        "published": i.get("published"),
                        "content_id": i.get("content_id"),
                    }
                    for i in items
                ],
            }
        )
    pages = [
        {"url": p["url"], "title": p["title"], "published": p.get("published")}
        for p in client.get_paginated(f"/courses/{course_id}/pages")
    ]
    assignments = [
        {
            "id": a["id"],
            "name": a["name"],
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "published": a.get("published"),
        }
        for a in client.get_paginated(f"/courses/{course_id}/assignments")
    ]
    return {"modules": modules, "pages": pages, "assignments": assignments}


def create_module(client: CanvasClient, course_id: int, name: str, position: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"module": {"name": name}}
    if position is not None:
        payload["module"]["position"] = position
    return client.post(f"/courses/{course_id}/modules", payload)


def _validate_module_item_target(
    client: CanvasClient,
    course_id: int,
    item_type: str,
    content_id: int | None,
    page_url: str | None,
) -> None:
    """Fail fast if the referenced content doesn't exist (Canvas would happily
    create a broken module item and return success)."""
    if item_type == "File" and content_id:
        client.get(f"/courses/{course_id}/files/{content_id}")
    elif item_type == "Assignment" and content_id:
        client.get(f"/courses/{course_id}/assignments/{content_id}")
    elif item_type == "Page" and page_url:
        client.get(f"/courses/{course_id}/pages/{page_url}")


def add_module_item(
    client: CanvasClient,
    course_id: int,
    module_id: int,
    item_type: str,
    title: str | None = None,
    content_id: int | None = None,
    page_url: str | None = None,
    external_url: str | None = None,
) -> dict[str, Any]:
    _validate_module_item_target(client, course_id, item_type, content_id, page_url)
    item: dict[str, Any] = {"type": item_type}
    if title:
        item["title"] = title
    if content_id is not None:
        item["content_id"] = content_id
    if page_url:
        item["page_url"] = page_url
    if external_url:
        item["external_url"] = external_url
    return client.post(f"/courses/{course_id}/modules/{module_id}/items", {"module_item": item})


def _reject_pre_escaped_html(body_html: str) -> None:
    """Catch bodies that were HTML-escaped before being passed in.

    A body full of &lt; entities with no real tags would be stored verbatim by
    Canvas and render as literal markup to students. Better to fail loudly.
    """
    stripped = body_html.replace("&lt;", "").replace("&gt;", "")
    if "&lt;" in body_html and "<" not in stripped:
        raise ValueError(
            "body_html appears to be HTML-escaped (contains &lt; but no real '<' tags). "
            "Pass raw HTML markup instead."
        )


def create_page(client: CanvasClient, course_id: int, title: str, body_html: str) -> dict[str, Any]:
    _reject_pre_escaped_html(body_html)
    return client.post(
        f"/courses/{course_id}/pages",
        {"wiki_page": {"title": title, "body": body_html, "published": False}},
    )


def get_page(client: CanvasClient, course_id: int, page_url: str) -> dict[str, Any]:
    p = client.get(f"/courses/{course_id}/pages/{page_url}")
    return {
        "page_url": p["url"],
        "title": p["title"],
        "published": p.get("published"),
        "body": p.get("body") or "",
    }


def update_page(
    client: CanvasClient,
    course_id: int,
    page_url: str,
    body_html: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    _reject_pre_escaped_html(body_html or "")
    wiki_page: dict[str, Any] = {}
    if body_html is not None:
        wiki_page["body"] = body_html
    if title is not None:
        wiki_page["title"] = title
    return client.put(f"/courses/{course_id}/pages/{page_url}", {"wiki_page": wiki_page})


def delete_page(client: CanvasClient, course_id: int, page_url: str) -> dict[str, Any]:
    return client.delete(f"/courses/{course_id}/pages/{page_url}")


def create_assignment(
    client: CanvasClient,
    course_id: int,
    name: str,
    description_html: str = "",
    due_at: str | None = None,
    points_possible: float | None = None,
    submission_types: list[str] | None = None,
) -> dict[str, Any]:
    assignment: dict[str, Any] = {"name": name, "description": description_html, "published": False}
    if due_at:
        assignment["due_at"] = due_at
    if points_possible is not None:
        assignment["points_possible"] = points_possible
    if submission_types:
        assignment["submission_types"] = submission_types
    return client.post(f"/courses/{course_id}/assignments", {"assignment": assignment})


def update_syllabus(client: CanvasClient, course_id: int, body_html: str) -> dict[str, Any]:
    return client.put(f"/courses/{course_id}", {"course": {"syllabus_body": body_html}})


def post_announcement(client: CanvasClient, course_id: int, title: str, message_html: str) -> dict[str, Any]:
    return client.post(
        f"/courses/{course_id}/discussion_topics",
        {"title": title, "message": message_html, "is_announcement": True},
    )


def update_module_item(
    client: CanvasClient,
    course_id: int,
    module_id: int,
    item_id: int,
    title: str | None = None,
    position: int | None = None,
    indent: int | None = None,
    content_id: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {}
    if title is not None:
        item["title"] = title
    if position is not None:
        item["position"] = position
    if indent is not None:
        item["indent"] = indent
    if content_id is not None:
        item["content_id"] = content_id
    return client.put(
        f"/courses/{course_id}/modules/{module_id}/items/{item_id}", {"module_item": item}
    )


def delete_module_item(
    client: CanvasClient, course_id: int, module_id: int, item_id: int
) -> dict[str, Any]:
    return client.delete(f"/courses/{course_id}/modules/{module_id}/items/{item_id}")


def reorder_module_items(
    client: CanvasClient, course_id: int, module_id: int, item_ids: list[int]
) -> list[dict[str, Any]]:
    """Reorder items by assigning positions 1..n in the given order.

    Assigning ascending positions in sequence converges even though each move
    shifts the neighbours' positions.
    """
    results = []
    for position, item_id in enumerate(item_ids, start=1):
        r = client.put(
            f"/courses/{course_id}/modules/{module_id}/items/{item_id}",
            {"module_item": {"position": position}},
        )
        results.append({"id": r["id"], "title": r.get("title"), "position": r.get("position")})
    return results


def delete_file(client: CanvasClient, file_id: int) -> dict[str, Any]:
    return client.delete(f"/files/{file_id}")


def set_folder_locked(
    client: CanvasClient, course_id: int, folder_path: str, locked: bool
) -> dict[str, Any]:
    """Lock/unlock a folder. A locked folder's files are hidden from students
    even if the files themselves are published — unpublished modules alone do
    NOT restrict access to the files inside them."""
    wanted = folder_path.strip("/").lower()
    for f in client.get_paginated(f"/courses/{course_id}/folders"):
        rel = f["full_name"].removeprefix("course files").lstrip("/")
        if rel.lower() == wanted:
            result = client.put(f"/folders/{f['id']}", {"locked": locked})
            return {"folder": rel, "id": f["id"], "locked": result.get("locked")}
    raise CanvasAPIError(0, f"No folder matching '{folder_path}' in course {course_id}", "")


def set_module_published(
    client: CanvasClient, course_id: int, module_id: int, published: bool
) -> dict[str, Any]:
    return client.put(
        f"/courses/{course_id}/modules/{module_id}", {"module": {"published": published}}
    )


def set_assignment_published(
    client: CanvasClient, course_id: int, assignment_id: int, published: bool
) -> dict[str, Any]:
    return client.put(
        f"/courses/{course_id}/assignments/{assignment_id}", {"assignment": {"published": published}}
    )
