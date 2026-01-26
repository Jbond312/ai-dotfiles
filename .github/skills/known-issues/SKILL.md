---
name: known-issues
description: "Known agent mistakes and corrections. Consult before executing scripts or taking actions to avoid repeating past errors."
---

# Known Issues

**Check your planned action against these known issues before proceeding.**

## Context Files

| #   | Mistake                                                                        | Correct Behaviour                                                                       |
| --- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| 1   | Assumed or hallucinated team name (e.g., used "CBI Platform" without checking) | Always read `.github/team-context.md` first and use the exact team name specified there |

**Rule:** Never assume Azure DevOps values (org, project, team name, team ID). Always read from `.github/team-context.md`.

## Script Arguments

| #   | Mistake                                                                  | Correct Behaviour                                                                                                     |
| --- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| 2   | Added unsupported `--max-results` argument to `get_sprint_work_items.py` | The script has no `--max-results` flag. Run the script without it and filter/limit results in your output to the user |

**Rule:** Only use arguments documented in the skill. Check `.github/skills/azure-devops-api/SKILL.md` for valid arguments:

- `get_sprint_work_items.py`: `--org`, `--project`, `--team`, `--state`, `--unassigned`, `--assigned-to`, `--type`
- `get_team_prs.py`: `--org`, `--project`, `--reviewer-id`, `--status`, `--exclude-author-id`

## Pre-Action Checklist

Before executing any Azure DevOps script:

1. ✓ Have I read `.github/team-context.md` for org, project, team values?
2. ✓ Am I using only documented script arguments?
3. ✓ Am I using scripts (not MCP) for team-filtered queries?
