"""Regression test for the folder-case, overwrite, and page-escaping bugs.

Runs against a real course you name (use an unpublished sandbox course, never
one with students), creating everything under clearly-marked test names, and
deletes all artifacts at the end regardless of pass/fail.

    uv run python scripts/regression_test.py <course_id>
"""

import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from canvas_mcp import content, files  # noqa: E402
from canvas_mcp.client import CanvasClient  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("usage: uv run python scripts/regression_test.py <course_id>  (unpublished sandbox course only)")
COURSE = int(sys.argv[1])
FOLDER = "MCP Regression Week 01"
PAGE_TITLE = "MCP Regression Page (delete me)"

client = CanvasClient()
failures: list[str] = []
module_id = None
page_url = None
file_id = None


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(label)


try:
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "regression_test_file.txt"
        local.write_text("version one\n")

        print("1-3. upload into mixed-case folder, link it in a module")
        up1 = files.upload_file(client, COURSE, str(local), FOLDER)
        file_id = up1["id"]
        module = content.create_module(client, COURSE, "MCP Regression Module (delete me)")
        module_id = module["id"]
        item = content.add_module_item(client, COURSE, module_id, "File", content_id=file_id)

        print("4. listing reports real casing")
        listing = files.canvas_file_map(client, COURSE)
        reported = next((p for p in listing if "regression_test_file" in p), None)
        check("path preserves case", reported == f"{FOLDER}/regression_test_file.txt", str(reported))

        print("5-6. round-trip the reported path through a replacing upload")
        local.write_text("version TWO, which is longer than version one\n")
        reported_folder = str(Path(reported).parent)
        up2 = files.upload_file(client, COURSE, str(local), reported_folder)
        file_id = up2["id"]

        folders = [
            f for f in client.get_paginated(f"/courses/{COURSE}/folders")
            if "regression" in f["full_name"].lower()
        ]
        check("no duplicate folder created", len(folders) == 1,
              str([f["full_name"] for f in folders]))
        listing = files.canvas_file_map(client, COURSE)
        copies = [p for p in listing if "regression_test_file" in p]
        check("exactly one copy of the file", len(copies) == 1, str(copies))
        check("new size stored", listing[copies[0]]["size"] == local.stat().st_size)

        items = list(client.get_paginated(f"/courses/{COURSE}/modules/{module_id}/items"))
        check("module item repointed to live file id",
              items and items[0]["content_id"] == up2["id"],
              f"item content_id={items[0]['content_id'] if items else '?'} vs file {up2['id']}")
        if up1["id"] != up2["id"]:
            check("replacement was reported", up2.get("replaced_file_id") == up1["id"])

        print("7-8. page bodies round-trip raw HTML")
        page = content.create_page(client, COURSE, PAGE_TITLE,
                                   "<h2>Head</h2><ol><li>a</li></ol><strong>b</strong>")
        page_url = page["url"]
        stored = content.get_page(client, COURSE, page_url)["body"]
        check("raw <h2> stored", "<h2>" in stored and "&lt;h2&gt;" not in stored)

        try:
            content.create_page(client, COURSE, "x", "&lt;h2&gt;escaped&lt;/h2&gt;")
            check("pre-escaped body rejected", False)
        except ValueError:
            check("pre-escaped body rejected", True)
finally:
    print("cleanup...")
    if page_url:
        content.delete_page(client, COURSE, page_url)
    if module_id:
        client.delete(f"/courses/{COURSE}/modules/{module_id}")
    if file_id:
        content.delete_file(client, file_id)
    for f in client.get_paginated(f"/courses/{COURSE}/folders"):
        if "regression" in f["full_name"].lower():
            client.delete(f"/folders/{f['id']}", {"force": True})
    print("cleanup done")

print()
print("ALL PASSED" if not failures else f"FAILED: {failures}")
sys.exit(1 if failures else 0)
