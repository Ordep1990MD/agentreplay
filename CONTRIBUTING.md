# Contributing

Start with a reproducible agent failure: expected state, actual state and the smallest sequence of tool calls that distinguishes them.

1. Run `python -m unittest discover -s tests -v`.
2. Add a fixture in `agentreplay/scenarios.py` and an independent regression test.
3. Keep scenario truth hidden from the agent-facing task/tools.
4. Include an intentionally failing policy or trace and explain the assertion it violates.
5. Update both READMEs when changing CLI behavior or built-in scenario counts.

Do not include live tokens, real messages, customer data or provider credentials. Use standard-library Python where practical. New integrations should begin with a narrow, well-defined task and documented simulator limitations. Do not add a passing assertion solely to improve the score.

Good first contributions: model-provider adapters with time/cost limits, independently verified MCP client configurations, accessible report improvements, deterministic webhook redelivery fixtures.
