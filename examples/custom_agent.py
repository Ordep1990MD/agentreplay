"""Replace this policy with your model's tool-calling loop.

Run from the project root:
    python -m agentreplay run --agent examples.custom_agent:run
"""
from agentreplay.agents import cautious


def run(call, task):
    # call(name, **arguments) returns JSON-compatible data or raises ToolError.
    # Your loop should expose the schemas from engine.tool_definitions().
    # Return completed, blocked, or failed. Never use real GitHub credentials.
    return cautious(call, task)
