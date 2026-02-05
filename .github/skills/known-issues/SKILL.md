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

<!-- | # | Mistake | Correct Behaviour | -->

## Testing

<!-- | # | Mistake | Correct Behaviour | -->

## Code Review

<!-- | # | Mistake | Correct Behaviour | -->

## Git & Commits

<!-- | # | Mistake | Correct Behaviour | -->

## SQL & Stored Procedures

<!-- | # | Mistake | Correct Behaviour | -->

## Adding New Issues

Add to the appropriate section using this format:

```markdown
| # | {What went wrong} | {What should happen instead} |
```

Use the next available number (currently 3).
