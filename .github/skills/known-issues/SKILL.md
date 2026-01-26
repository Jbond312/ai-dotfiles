---
name: known-issues
description: "Known agent mistakes and how to avoid them. Use before running scripts, executing commands, or taking actions in Azure DevOps workflows. Triggers on: before running, check issues, avoid mistakes, script arguments, team name, context files."
---

# Known Issues

**Check your planned action against these known issues before proceeding.**

## Script Arguments

| #   | Mistake                                                                                        | Correct Behaviour                                                                                                                                                                                 |
| --- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Added unsupported arguments to scripts (e.g., `--max-results`, `--org`, `--project`, `--team`) | Scripts read org/project/team from environment variables. Only use documented arguments: `--state`, `--unassigned`, `--assigned-to`, `--type` for work items; `--status`, `--include-own` for PRs |

**Rule:** Scripts get Azure DevOps configuration from environment variables (`AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_TEAM`, etc.). Do not pass org/project/team as arguments.

## MCP vs Scripts

| #   | Mistake                                         | Correct Behaviour                                                                                                 |
| --- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 2   | Used MCP to query sprint work items or team PRs | MCP cannot filter by Area Path or team reviewer. Use Python scripts in `.github/skills/azure-devops-api/scripts/` |

**Rule:** Use scripts for team-filtered queries, MCP only for individual item lookups and updates.

## Pre-Action Checklist

Before executing any Azure DevOps script:

1. ✓ Am I using only documented script arguments?
2. ✓ Am I using scripts (not MCP) for team-filtered queries?
3. ✓ Are the required environment variables configured? (Script will error if not)
