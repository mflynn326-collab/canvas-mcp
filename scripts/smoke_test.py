"""Quick auth check: run after putting your token in .env.

    uv run python scripts/smoke_test.py
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from canvas_mcp.client import CanvasClient  # noqa: E402
from canvas_mcp.content import list_courses  # noqa: E402

client = CanvasClient()
me = client.get("/users/self")
print(f"Authenticated as: {me.get('name')} ({me.get('primary_email', 'email hidden')})")

courses = list_courses(client)
if not courses:
    print("No courses found where you are a teacher/TA.")
for c in courses:
    print(f"  [{c['id']}] {c['course_code']} - {c['name']} ({c['workflow_state']}, term: {c['term']})")
