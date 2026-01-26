---
name: azure-devops-api
description: "Scripts for Azure DevOps REST API. Use instead of MCP when you need team-filtered PR lists, sprint work items with Area Path filtering, or other data the MCP cannot provide."
---

# Azure DevOps API Scripts

**Use these scripts instead of MCP** for team-filtered queries. The Azure DevOps MCP cannot:

- Filter work items by team Area Path
- Filter work items by current iteration (`@CurrentIteration`)
- Filter PRs by team reviewer

Use MCP only for: fetching individual items by ID, creating/updating work items, creating PRs.

## Prerequisites

- Python 3.6+
- `AZURE_DEVOPS_PAT` environment variable with Code (Read), Work Items (Read) permissions

Configure in `.vscode/settings.json` (add to `.gitignore`):

```json
{
  "terminal.integrated.env.windows": { "AZURE_DEVOPS_PAT": "your-pat" }
}
```

## get_sprint_work_items.py

Query work items from current sprint for a team using WIQL with `@CurrentIteration` macro.

```bash
# Unassigned items (for picking up work)
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" --project "your-project" --team "Team Name" --unassigned

# Items assigned to current user
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" --project "your-project" --team "Team Name" --assigned-to "@me"

# Items by state
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" --project "your-project" --team "Team Name" --state "In Progress"
```

**Arguments:** `--org`, `--project`, `--team` (required), `--state`, `--unassigned`, `--assigned-to`, `--type`

**Note:** Team name must be exact (case-sensitive) — it's used to resolve `@CurrentIteration` and construct the Area Path filter.

## get_team_prs.py

Get PRs where a team/user is assigned as reviewer.

```bash
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "your-org" --project "your-project" --reviewer-id "team-guid"
```

**Arguments:** `--org`, `--project`, `--reviewer-id` (required), `--status`, `--exclude-author-id`

## When to Use

| Need                                | Use    |
| ----------------------------------- | ------ |
| PRs filtered by team reviewer       | Script |
| Sprint work items with Area Path    | Script |
| PR metadata, work item by ID        | MCP    |
| Creating/updating work items or PRs | MCP    |

Read org/project/team from `.github/team-context.md`.
