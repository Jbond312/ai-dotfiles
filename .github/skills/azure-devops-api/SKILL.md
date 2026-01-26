---
name: azure-devops-api
description: 'Query Azure DevOps sprint work items and team PRs using Python scripts. Use when asked to find work items, show sprint backlog, list PRs for review, check what is available to pick up, or answer "what next" / "what should I work on". Triggers on: work items, sprint, backlog, PRs, pull requests, available work, unassigned items, team review.'
---

# Azure DevOps API Scripts

**Use these scripts instead of MCP** for team-filtered queries. The Azure DevOps MCP cannot:

- Filter work items by team Area Path
- Filter work items by current iteration (`@CurrentIteration`)
- Filter PRs by team reviewer

Use MCP only for: fetching individual items by ID, creating/updating work items, creating PRs.

## Prerequisites

Configure these environment variables in `.vscode/settings.json` (add settings.json to `.gitignore`):

```json
{
  "terminal.integrated.env.windows": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  },
  "terminal.integrated.env.osx": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  },
  "terminal.integrated.env.linux": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  }
}
```

**Required:** `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_TEAM`
**Optional:** `AZURE_DEVOPS_TEAM_ID` (for PR queries), `AZURE_DEVOPS_USER_ID` (to exclude own PRs)

## get_sprint_work_items.py

Query work items from current sprint for a team.

```bash
# Unassigned items (for picking up work)
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py --unassigned

# Items assigned to current user
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py --assigned-to "@me"

# Items by state
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py --state "In Progress"
```

**Arguments:** `--state`, `--unassigned`, `--assigned-to`, `--type`

## get_team_prs.py

Get PRs where the team is assigned as reviewer.

```bash
# PRs needing team review (excluding your own)
python .github/skills/azure-devops-api/scripts/get_team_prs.py

# Include your own PRs
python .github/skills/azure-devops-api/scripts/get_team_prs.py --include-own
```

**Arguments:** `--status`, `--include-own`

## When to Use

| Need                                | Use    |
| ----------------------------------- | ------ |
| PRs filtered by team reviewer       | Script |
| Sprint work items with Area Path    | Script |
| PR metadata, work item by ID        | MCP    |
| Creating/updating work items or PRs | MCP    |
