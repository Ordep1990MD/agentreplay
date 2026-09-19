# Release candidate 0.1.0

## Included

- Deterministic issue simulator with ten fixtures and nine checks per run.
- Scripted naive and cautious baselines; Python agent adapter contract.
- Minimal MCP stdio tools server with immutable single-scenario sessions.
- Input-trace replay, offline HTML reports and JSON results.
- English and Spanish READMEs, contribution and security guidance, MIT license.
- GitHub Actions workflow for Python 3.10 / 3.12 / 3.13.

## Verification performed

- 22 unittest tests passed under Python 3.12.14.
- Demo produced naive 3/10 and cautious 10/10.
- Local wheel built and installed into a virtual environment.
- Installed CLI passed timeout-after-write from outside the source directory.
- Subprocess tests exercised MCP initialize, tool discovery, calls, finish,
  post-finish rejection, malformed JSON and incomplete EOF.

## Launch preparation additions

- Offline interactive demo generated from simulator traces.
- Actionable report recommendations and check-level comparison script.
- Contribution templates and prepared profile/publication kit.

## Not yet verified

No real model evaluation, independent MCP client interoperability check,
remote GitHub Actions run, or Python 3.10/3.13 execution has occurred.
This is a development alpha, not a production security guarantee.

## Distribution

Source repository: https://github.com/Ordep1990MD/agentreplay
This is an alpha source release. The package name is provisional and has not
been registered on PyPI. Check GitHub Actions for the latest CI status.
