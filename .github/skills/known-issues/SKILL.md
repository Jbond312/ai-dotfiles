---
name: known-issues
description: "Known agent mistakes and how to avoid them. Use before running scripts, executing commands, or taking actions in Azure DevOps workflows. Triggers on: before running, check issues, avoid mistakes, script arguments, team name, context files."
---

# Known Issues

**Check your planned action against these known issues before proceeding.**

When you encounter a new mistake that isn't listed here, **add it** to the appropriate section so future runs don't repeat it.

## Scripts & CLI

| #   | Mistake | Correct Behaviour |
| --- | ------- | ----------------- |
| 1   | Added unsupported arguments to scripts (e.g., `--max-results`, `--org`, `--project`, `--team`) | Scripts read org/project/team from environment variables. Only use documented arguments: `--state`, `--unassigned`, `--assigned-to`, `--type` for work items; `--status`, `--include-own` for PRs |

**Rule:** Scripts get Azure DevOps configuration from environment variables (`AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_TEAM`, etc.). Do not pass org/project/team as arguments.

## MCP & Azure DevOps

| #   | Mistake | Correct Behaviour |
| --- | ------- | ----------------- |
| 2   | Used MCP to query sprint work items or team PRs | MCP cannot filter by Area Path or team reviewer. Use Python scripts in `.github/skills/azure-devops-api/scripts/` |

**Rule:** Use scripts for team-filtered queries, MCP only for individual item lookups and updates.

## Coding & Implementation

<!-- Add entries as they are discovered -->
<!-- Example:
| #   | Mistake | Correct Behaviour |
| --- | ------- | ----------------- |
| 3   | Used DateTime.Now in handler | Inject IDateTimeProvider or TimeProvider |
-->

No issues recorded yet.

## Testing

<!-- Add entries as they are discovered -->
<!-- Example:
| #   | Mistake | Correct Behaviour |
| --- | ------- | ----------------- |
| 4   | Tests passed with Total: 0 | Verify test discovery before trusting results |
-->

No issues recorded yet.

## Code Review

<!-- Add entries as they are discovered -->

No issues recorded yet.

## Git & Commits

<!-- Add entries as they are discovered -->

No issues recorded yet.

## Pre-Action Checklist

Before executing any action, scan the relevant section above:

1. Am I using only documented script arguments?
2. Am I using scripts (not MCP) for team-filtered queries?
3. Are the required environment variables configured?
4. Does my planned action match any known mistake above?

## Adding New Issues

When you discover a repeating mistake, add it to the appropriate section using this format:

```markdown
| # | {What went wrong} | {What should happen instead} |
```

Use the next available number. Include enough context that a future agent can recognise the same situation.
