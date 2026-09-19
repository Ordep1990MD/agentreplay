# Security scope

AgentReplay is a local integration simulator. It never contacts GitHub or requires credentials. It is not an OS sandbox, agent firewall or security certification.

Custom Python agents are trusted code. MCP clients should have only simulated tools available during a benchmark. Full tool arguments/responses appear in reports, so use synthetic data and inspect artifacts before publishing them.

For public code-quality problems, open an issue with a minimal synthetic reproduction. For a potentially sensitive vulnerability, use GitHub private vulnerability reporting if enabled on the published repository. If it is unavailable, open a minimal issue asking for a private reporting channel without including exploit details or secrets.
