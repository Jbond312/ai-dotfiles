---
name: azure-devops-api
description: "Scripts for interacting with Azure DevOps REST API directly. Use these scripts instead of the Azure DevOps MCP when you need team-filtered PR lists or other data the MCP does not provide."
---

# Azure DevOps API Scripts

This skill provides Python scripts that interact with the Azure DevOps REST API directly. Use these scripts when the Azure DevOps MCP server doesn't provide the data you need—particularly for filtering PRs by team reviewer (an MCP limitation).

## Prerequisites

1. **Python 3.6+** installed
2. **AZURE_DEVOPS_PAT** environment variable set with a Personal Access Token that has:
   - Code (Read) — for PR and repository access
   - Work Items (Read) — if querying work items
   - Build (Read) — if querying pipelines

### Setting up the PAT

The recommended approach is to configure VS Code to provide the PAT to all terminals. Add to `.vscode/settings.json`:

```json
{
  "terminal.integrated.env.linux": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  },
  "terminal.integrated.env.osx": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  },
  "terminal.integrated.env.windows": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  }
}
```

**Important:** Add `.vscode/settings.json` to `.gitignore` to avoid committing your PAT.

A template is provided at `.vscode/settings.template.json` — copy it to `settings.json` and add your PAT.

## Available Scripts

### get_sprint_work_items.py

Query work items from the current sprint board for a team.

Uses the Azure DevOps REST API to:

1. Get the current iteration for the specified team
2. Query work items filtered by Area Path and Iteration Path

**Why use this instead of MCP?** The Microsoft Azure DevOps MCP doesn't expose a WIQL query tool, so we can't filter work items by both Area Path (team ownership) and current iteration (sprint).

**Usage:**

```bash
# Get unassigned items in current sprint (for picking up work)
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" \
  --project "your-project" \
  --team "Your Team Name" \
  --unassigned

# Get in-progress items (to check on colleagues)
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" \
  --project "your-project" \
  --team "Your Team Name" \
  --state "In Progress"

# Get items assigned to a specific user
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" \
  --project "your-project" \
  --team "Your Team Name" \
  --assigned-to "user@example.com"

# Get all items in current sprint
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py \
  --org "your-org" \
  --project "your-project" \
  --team "Your Team Name"
```

**Arguments:**

| Argument        | Required | Description                                                           |
| --------------- | -------- | --------------------------------------------------------------------- |
| `--org`         | Yes      | Azure DevOps organization name                                        |
| `--project`     | Yes      | Azure DevOps project name                                             |
| `--team`        | Yes      | Team name (case-sensitive, must match exactly)                        |
| `--state`       | No       | Filter by state (can be repeated for multiple states)                 |
| `--unassigned`  | No       | Only return unassigned work items                                     |
| `--assigned-to` | No       | Filter by assigned user email or display name                         |
| `--type`        | No       | Work item types to include (default: "Product Backlog Item", "Spike") |

**Output:**

```json
{
  "iteration": {
    "name": "Sprint 42",
    "path": "PaymentsPlatform\\Sprint 42"
  },
  "team": "Platform Team",
  "areaPath": "PaymentsPlatform\\Platform Team",
  "count": 3,
  "workItems": [
    {
      "id": 12345,
      "type": "Product Backlog Item",
      "title": "Add payment validation",
      "state": "New",
      "assignedTo": "Unassigned",
      "effort": 5,
      "priority": 1000000,
      "daysSinceChange": 2,
      "webUrl": "https://dev.azure.com/..."
    }
  ]
}
```

**Important:** The team name must match exactly (case-sensitive) what's configured in Azure DevOps. The script uses it to construct:

- Area Path: `{Project}\{Team}` — filters to work items owned by your team
- Iteration query: Gets the team's current iteration

---

### get_team_prs.py

Get pull requests where a specific reviewer (team or user) is assigned.

Uses the project-level PR endpoint with `searchCriteria.reviewerId` filter—a single API call.

**Usage:**

```bash
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "your-org" \
  --project "your-project" \
  --reviewer-id "team-or-user-guid" \
  [--status active] \
  [--exclude-author-id "user-guid-to-exclude"]
```

**Arguments:**

| Argument              | Required | Description                                                    |
| --------------------- | -------- | -------------------------------------------------------------- |
| `--org`               | Yes      | Azure DevOps organization name                                 |
| `--project`           | Yes      | Azure DevOps project name                                      |
| `--reviewer-id`       | Yes      | Reviewer GUID (can be team ID or user ID)                      |
| `--status`            | No       | PR status: `active` (default), `completed`, `abandoned`, `all` |
| `--exclude-author-id` | No       | Exclude PRs by this author (useful to filter out your own PRs) |

**Output:**

```json
{
  "count": 2,
  "pullRequests": [
    {
      "id": 123,
      "repository": "my-service",
      "title": "Add payment validation",
      "author": "Jane Smith",
      "authorId": "abc-123-...",
      "status": "active",
      "sourceBranch": "backlog/12345-add-payment-validation",
      "targetBranch": "main",
      "createdDate": "2024-01-15T10:30:00Z",
      "ageDays": 3,
      "isDraft": false,
      "reviewers": [{ "name": "Platform Team", "vote": 0, "isRequired": true }],
      "webUrl": "https://dev.azure.com/org/project/_git/repo/pullrequest/123"
    }
  ]
}
```

## Reading Configuration from Project Context

The script requires org, project, and reviewer-id. Read these from `.github/project-context.md`:

```markdown
## Azure DevOps

- **Organization:** contoso
- **Project:** payments-platform

## Team

- **Team name:** Platform Team
- **Team ID:** a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

When calling the script, extract these values and pass them as arguments.

## Example: Finding PRs for Your Team

```bash
# Set PAT (or configure in .vscode/settings.json)
export AZURE_DEVOPS_PAT="your-pat"

# Get team ID from project context
TEAM_ID="team-guid-from-project-context"

# Get PRs where your team is a reviewer
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "contoso" \
  --project "payments-platform" \
  --reviewer-id "$TEAM_ID"

# Or exclude your own PRs (if you know your user ID)
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "contoso" \
  --project "payments-platform" \
  --reviewer-id "$TEAM_ID" \
  --exclude-author-id "your-user-guid"
```

## Error Handling

The script returns JSON error objects on failure:

```json
{
  "error": true,
  "status": 401,
  "message": "Unauthorized",
  "details": "..."
}
```

Common errors:

| Error                                           | Cause                    | Solution                        |
| ----------------------------------------------- | ------------------------ | ------------------------------- |
| `AZURE_DEVOPS_PAT environment variable not set` | PAT not configured       | Set the environment variable    |
| `401 Unauthorized`                              | PAT invalid or expired   | Generate a new PAT              |
| `404 Not Found`                                 | Project doesn't exist    | Check project name              |
| `403 Forbidden`                                 | PAT lacks required scope | Add required permissions to PAT |

## When to Use This Script vs MCP

| Need                                             | Use                                                       |
| ------------------------------------------------ | --------------------------------------------------------- |
| PRs filtered by team/user reviewer               | Script (`get_team_prs.py`)                                |
| Current sprint board for a team (with Area Path) | Script (`get_sprint_work_items.py`)                       |
| Unassigned items in current sprint               | Script (`get_sprint_work_items.py --unassigned`)          |
| In-progress items to check on colleagues         | Script (`get_sprint_work_items.py --state "In Progress"`) |
| PR metadata (title, status, reviewers)           | MCP or script                                             |
| Work item details by ID                          | MCP                                                       |
| Pipeline status                                  | MCP                                                       |
| Creating/updating work items                     | MCP                                                       |
| Creating/updating PRs                            | MCP                                                       |

**Rule of thumb:** Use the MCP for writes and basic queries. Use these scripts when you need:

- PRs filtered by team reviewer
- Work items filtered by Area Path AND current iteration (sprint board)
