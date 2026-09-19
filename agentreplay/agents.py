"""Scripted baselines, NOT AI models and NOT evidence of LLM performance."""
from .engine import ToolError


def cautious(call, task):
    """Generic reconcile-before-retry policy; no access to scenario identity."""
    for _ in range(12):
        page = 1
        while True:
            try:
                result = call("list_issues", repo=task["repo"], page=page)
            except ToolError as exc:
                if exc.code == "rate_limited":
                    call("wait", seconds=exc.details["retry_after"])
                    continue
                if exc.code in ("permission_denied", "approval_required"):
                    return "blocked"
                raise
            if any(i["title"] == task["title"] and i["body"] == task["body"] for i in result["issues"]):
                return "completed"
            page = result["next_page"]
            if page is None:
                break
        try:
            call("create_issue", repo=task["repo"], title=task["title"], body=task["body"])
            return "completed"
        except ToolError as exc:
            if exc.code in ("permission_denied", "approval_required"):
                return "blocked"
            if exc.code != "timeout":
                raise
            # Both timeout variants look identical. Read again to discover reality.
    return "failed"


def naive(call, task):
    """An intentionally flawed baseline: writes immediately, retries blindly."""
    for _ in range(3):
        try:
            call("create_issue", repo=task["repo"], title=task["title"], body=task["body"])
            return "completed"
        except ToolError:
            pass
    return "completed"
