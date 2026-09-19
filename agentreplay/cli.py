import argparse
import importlib
import json
import sys
from pathlib import Path
from . import __version__
from .agents import cautious, naive
from .engine import Sandbox, ToolError
from .report import write_reports
from .scenarios import SCENARIOS, task


def load_agent(name):
    if name in ("cautious", "naive"):
        return {"cautious": cautious, "naive": naive}[name]
    module, sep, attribute = name.partition(":")
    if not sep:
        raise ValueError("Agent must be cautious, naive, or module:function")
    agent = getattr(importlib.import_module(module), attribute)
    if not callable(agent):
        raise ValueError("Agent entrypoint must be callable")
    return agent


def run_one(scenario, agent):
    box = Sandbox(scenario)
    error = None
    try:
        outcome = agent(box.call, task())
        if outcome not in ("completed", "blocked", "failed"):
            raise ValueError("Agent must return completed, blocked, or failed")
    except Exception as exc:
        outcome = "failed"
        error = f"{type(exc).__name__}: {exc}"
    result = box.evaluate(outcome)
    if error:
        result["agent_error"] = error
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="AgentReplay: test agent actions against simulated integration failures.")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("list", help="List the ten built-in scenarios")
    run = subs.add_parser("run", help="Run a scripted baseline or a trusted Python agent")
    run.add_argument("--agent", default="cautious", help="cautious, naive, or module:function (executes local code)")
    run.add_argument("--scenario", choices=list(SCENARIOS) + ["all"], default="all")
    run.add_argument("--output", default="artifacts/run")
    demo = subs.add_parser("demo", help="Compare both scripted policies offline")
    demo.add_argument("--output", default="artifacts/demo")
    replay = subs.add_parser("replay", help="Re-execute tool inputs from a JSON trace against a fresh fixture")
    replay.add_argument("trace", type=Path)
    replay.add_argument("--output", default="artifacts/replay")
    serve = subs.add_parser("serve", help="Start a single-scenario MCP stdio server")
    serve.add_argument("--scenario", choices=list(SCENARIOS), required=True)
    serve.add_argument("--output", default="artifacts/mcp")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for name, spec in SCENARIOS.items():
                print(f"{name:24} {spec['description']}")
            return 0
        if args.command == "serve":
            from .mcp import serve
            return serve(args.scenario, args.output)
        if args.command == "demo":
            for label, agent in (("naive", naive), ("cautious", cautious)):
                results = [run_one(name, agent) for name in SCENARIOS]
                summary = write_reports(results, Path(args.output) / label, f"Scripted baseline: {label} (not an AI model)")
                print(f"{label}: {summary['passed']}/{summary['total']} passed — {args.output}/{label}/report.html")
            print("Demo completed. Naive failures are intentional. Use run for CI pass/fail gating.")
            return 0
        if args.command == "replay":
            payload = json.loads(args.trace.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("benchmark_version") != __version__:
                raise ValueError("Trace must use schema_version 1 and benchmark_version 0.1.0")
            box = Sandbox(payload["scenario"])
            if not isinstance(payload["actions"], list) or len(payload["actions"]) > 40:
                raise ValueError("actions must be an array of at most 40 tool calls")
            for action in payload["actions"]:
                if not isinstance(action, dict) or not isinstance(action.get("tool"), str) or not isinstance(action.get("arguments"), dict):
                    raise ValueError("Each action needs tool and arguments")
                try:
                    box.call(action["tool"], **action["arguments"])
                except ToolError:
                    pass
            if payload.get("outcome") not in ("completed", "blocked", "failed"):
                raise ValueError("Invalid outcome")
            results = [box.evaluate(payload["outcome"])]
            label = "Replayed tool inputs (not a fresh agent run)"
        else:
            agent = load_agent(args.agent)
            names = SCENARIOS if args.scenario == "all" else [args.scenario]
            results = [run_one(name, agent) for name in names]
            label = f"Agent: {args.agent}" + (" (scripted baseline, not an AI model)" if args.agent in ("cautious", "naive") else "")
        summary = write_reports(results, args.output, label)
        for r in results:
            print(f"{'PASS' if r['passed'] else 'FAIL'} {r['scenario']} ({r['calls']} calls)")
        print(f"{summary['passed']}/{summary['total']} passed — {args.output}/report.html")
        return 0 if summary["passed"] == summary["total"] else 1
    except (ValueError, KeyError, TypeError, OSError, ImportError, AttributeError) as exc:
        print(f"agentreplay: {exc}", file=sys.stderr)
        return 2
