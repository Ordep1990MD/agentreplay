import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from agentreplay.agents import cautious, naive
from agentreplay.cli import run_one
from agentreplay.engine import Sandbox, ToolError
from agentreplay.mcp import Server
from agentreplay.report import write_reports
from agentreplay.scenarios import SCENARIOS, REPO, TITLE, BODY

ARGS = dict(repo=REPO, title=TITLE, body=BODY)

class EvaluationTests(unittest.TestCase):
    def test_reference_policy_all_fixtures(self):
        for name in SCENARIOS:
            with self.subTest(name=name):
                self.assertTrue(run_one(name, cautious)["passed"])

    def test_naive_fails_seven_known_cases(self):
        self.assertEqual({n for n in SCENARIOS if not run_one(n, naive)["passed"]}, {"timeout-after-write", "permission-denied", "existing-duplicate", "paginated-duplicate", "approval-required", "rate-limit", "prompt-injection"})

    def test_timeouts_identical_but_state_differs(self):
        boxes = [Sandbox("timeout-before-write"), Sandbox("timeout-after-write")]
        errors = []
        for box in boxes:
            with self.assertRaises(ToolError) as caught:
                box.call("create_issue", **ARGS)
            errors.append(caught.exception.payload())
        self.assertEqual(errors[0], errors[1])
        self.assertEqual([len(b.issues) for b in boxes], [0, 1])

    def test_blind_retry_duplicates(self):
        result = run_one("timeout-after-write", naive)
        self.assertEqual(len(result["final_issues"]), 2)
        self.assertFalse(result["checks"]["goal_state"])

    def test_noop_cannot_claim_success_or_blocked(self):
        self.assertFalse(run_one("happy-path", lambda c, t: "completed")["passed"])
        self.assertFalse(run_one("permission-denied", lambda c, t: "blocked")["passed"])

    def test_scope_attempt_is_failure(self):
        box = Sandbox("prompt-injection")
        with self.assertRaises(ToolError):
            box.call("create_issue", **{**ARGS, "repo": "demo/private"})
        box.call("create_issue", **ARGS)
        self.assertFalse(box.evaluate("completed")["checks"]["scope_respected"])

    def test_invented_content_fails(self):
        box = Sandbox("happy-path")
        box.call("create_issue", **{**ARGS, "body": "invented"})
        result = box.evaluate("completed")
        self.assertFalse(result["checks"]["goal_state"])
        self.assertFalse(result["checks"]["no_unintended_changes"])

    def test_denials_do_not_mutate(self):
        for name in ("permission-denied", "approval-required"):
            box = Sandbox(name)
            with self.assertRaises(ToolError):
                box.call("create_issue", **ARGS)
            self.assertEqual(box.issues, [])
            self.assertTrue(box.evaluate("blocked")["passed"])

    def test_backoff_violation_persists(self):
        box = Sandbox("rate-limit")
        for _ in range(2):
            with self.assertRaises(ToolError):
                box.call("list_issues", repo=REPO)
        box.call("wait", seconds=3)
        box.call("create_issue", **ARGS)
        self.assertFalse(box.evaluate("completed")["checks"]["retry_delay_respected"])

    def test_isolation(self):
        box = Sandbox("existing-duplicate")
        result = box.call("list_issues", repo=REPO)
        result["issues"][0]["title"] = "tampered"
        self.assertEqual(box.issues[0]["title"], TITLE)
        box.issues.clear()
        self.assertEqual(len(Sandbox("existing-duplicate").issues), 1)

    def test_budget(self):
        box = Sandbox("happy-path", max_calls=1)
        box.call("get_task")
        with self.assertRaises(ToolError):
            box.call("get_task")
        self.assertEqual(len(box.trace), 1)
        self.assertFalse(box.evaluate("completed")["checks"]["call_budget"])

    def test_invalid_inputs(self):
        for name, args in [("list_issues", {"repo": REPO, "page": True}), ("wait", {"seconds": -1}), ("create_issue", {**ARGS, "approved": True}), ("create_issue", {**ARGS, "title": ""}), ("unknown", {})]:
            box = Sandbox("happy-path")
            with self.assertRaises(ToolError):
                box.call(name, **args)
            self.assertEqual(box.issues, [])

    def test_deterministic(self):
        self.assertEqual(run_one("rate-limit", cautious), run_one("rate-limit", cautious))

class ProtocolTests(unittest.TestCase):
    def test_stdio_full_session(self):
        with tempfile.TemporaryDirectory() as temp:
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "create_issue", "arguments": ARGS}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "finish", "arguments": {"outcome": "completed"}}},
                {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "create_issue", "arguments": ARGS}},
            ]
            proc = subprocess.run([sys.executable, "-m", "agentreplay", "serve", "--scenario", "happy-path", "--output", temp], input="bad json\n" + "\n".join(json.dumps(m) for m in messages) + "\n", text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            responses = [json.loads(line) for line in proc.stdout.splitlines()]
            self.assertEqual(len(responses), 6)
            self.assertEqual(responses[0]["error"]["code"], -32700)
            self.assertEqual(len(responses[2]["result"]["tools"]), 5)
            self.assertTrue(responses[-1]["result"]["isError"])
            report = json.loads((Path(temp) / "results.json").read_text())
            self.assertEqual(len(report["results"][0]["final_issues"]), 1)
            self.assertTrue(report["results"][0]["passed"])

    def test_eof_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run([sys.executable, "-m", "agentreplay", "serve", "--scenario", "happy-path", "--output", temp], input="", text=True, capture_output=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(json.loads((Path(temp) / "results.json").read_text())["results"][0]["outcome"], "incomplete")

    def test_lifecycle_and_malformed(self):
        with tempfile.TemporaryDirectory() as temp:
            server = Server("happy-path", temp)
            for message in [[], {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": []}]:
                self.assertIn("error", server.dispatch(message))

class DeliveryTests(unittest.TestCase):
    def test_html_escaping(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_one("happy-path", cautious)
            result["description"] = '<script>alert("test")</script>'
            write_reports([result], temp, "<img src=x>")
            report = (Path(temp) / "report.html").read_text()
            self.assertNotIn("<script>", report)
            self.assertNotIn("<img src=x>", report)
            self.assertIn("&lt;script&gt;", report)

    def test_replay_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run([sys.executable, "-m", "agentreplay", "replay", "examples/duplicate-timeout.json", "--output", temp], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1, proc.stderr)

    def test_custom_agent_and_invalid_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = subprocess.run([sys.executable, "-m", "agentreplay", "run", "--agent", "examples.custom_agent:run", "--output", temp], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            bad = Path(temp) / "bad.json"
            bad.write_text('{}')
            proc = subprocess.run([sys.executable, "-m", "agentreplay", "replay", str(bad)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)

if __name__ == "__main__":
    unittest.main()
