---
name: azure-devops-api
description: "Scripts for interacting with Azure DevOps REST API directly. Use these scripts instead of the Azure DevOps MCP when you need PR diffs, team-filtered PR lists, or other data the MCP does not provide."
---

# Azure DevOps API Scripts

This skill provides Python scripts that interact with the Azure DevOps REST API directly. Use these scripts when the Azure DevOps MCP server doesn't provide the data you need—particularly for:

- Getting PR diffs and file changes (MCP limitation)
- Filtering PRs by team reviewer (MCP limitation)
- Any other Azure DevOps data not exposed by the MCP

## Prerequisites

1. **Python 3.6+** installed
2. **AZURE_DEVOPS_PAT** environment variable set with a Personal Access Token that has:
   - Code (Read) — for PR and repository access
   - Work Items (Read) — if querying work items
   - Build (Read) — if querying pipelines

The PAT should be set before running the scripts:

```bash
export AZURE_DEVOPS_PAT="your-pat-token-here"
```

## Available Scripts

### get_team_prs.py

Get pull requests where a specific team (or user) is assigned as a reviewer.

**Usage:**

```bash
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "your-org" \
  --project "your-project" \
  --team-id "team-guid-here" \
  [--user-id "user-guid-here"] \
  [--status active] \
  [--exclude-author "user-guid-to-exclude"]
```

**Arguments:**

| Argument           | Required | Description                                                    |
| ------------------ | -------- | -------------------------------------------------------------- |
| `--org`            | Yes      | Azure DevOps organization name                                 |
| `--project`        | Yes      | Azure DevOps project name                                      |
| `--team-id`        | Yes      | Team GUID to filter by                                         |
| `--user-id`        | No       | Additional user GUID to include                                |
| `--status`         | No       | PR status: `active` (default), `completed`, `abandoned`, `all` |
| `--exclude-author` | No       | Exclude PRs by this author (useful to filter out your own PRs) |

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
      "authorEmail": "jane@example.com",
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

---

### get_pr_diff.py

Get the changed files and optionally their content for a pull request.

**Usage:**

```bash
python .github/skills/azure-devops-api/scripts/get_pr_diff.py \
  --org "your-org" \
  --project "your-project" \
  --repo "repository-name" \
  --pr-id 123 \
  [--file "src/path/to/file.cs"] \
  [--include-content]
```

**Arguments:**

| Argument            | Required | Description                                            |
| ------------------- | -------- | ------------------------------------------------------ |
| `--org`             | Yes      | Azure DevOps organization name                         |
| `--project`         | Yes      | Azure DevOps project name                              |
| `--repo`            | Yes      | Repository name                                        |
| `--pr-id`           | Yes      | Pull request ID                                        |
| `--file`            | No       | Specific file to get content for                       |
| `--include-content` | No       | Include full file content for all files (can be large) |

**Output (without --include-content):**

```json
{
  "pullRequest": {
    "id": 123,
    "title": "Add payment validation",
    "description": "Adds balance validation before processing payments",
    "author": "Jane Smith",
    "sourceBranch": "backlog/12345-add-payment-validation",
    "targetBranch": "main",
    "status": "active",
    "isDraft": false
  },
  "commits": {
    "source": "abc123...",
    "target": "def456..."
  },
  "summary": {
    "totalFiles": 4,
    "additions": 3,
    "deletions": 0
  },
  "changedFiles": [
    {
      "path": "/src/Features/Payments/CreatePayment/CreatePaymentHandler.cs",
      "changeType": "Modified"
    },
    {
      "path": "/src/Features/Payments/CreatePayment/CreatePaymentValidator.cs",
      "changeType": "Added"
    },
    {
      "path": "/tests/Payments/CreatePaymentTests.cs",
      "changeType": "Modified"
    }
  ]
}
```

**Output (with --include-content or --file):**

When content is included, each file in `changedFiles` will also have:

```json
{
  "path": "/src/Features/Payments/CreatePayment/CreatePaymentHandler.cs",
  "changeType": "Modified",
  "content": "// Full file content from PR branch...",
  "originalContent": "// Original file content from target branch..."
}
```

## Reading Configuration from Project Context

These scripts require org, project, and team-id. Read these from `.github/project-context.md`:

```markdown
## Team

- **Team name:** Platform Team
- **Team ID:** a1b2c3d4-e5f6-7890-abcd-ef1234567890

## Azure DevOps

- **Organization:** contoso
- **Project:** payments-platform
```

When calling the scripts, extract these values and pass them as arguments.

## Example: Finding PRs to Review

```bash
# Set PAT
export AZURE_DEVOPS_PAT="your-pat"

# Get current user ID (you'll need to know this or get it from az cli)
USER_ID="current-user-guid"

# Get team ID from project context
TEAM_ID="team-guid-from-project-context"

# Get PRs for review, excluding your own
python .github/skills/azure-devops-api/scripts/get_team_prs.py \
  --org "contoso" \
  --project "payments-platform" \
  --team-id "$TEAM_ID" \
  --user-id "$USER_ID" \
  --exclude-author "$USER_ID"
```

## Example: Reviewing a PR

```bash
# Get overview of changed files
python .github/skills/azure-devops-api/scripts/get_pr_diff.py \
  --org "contoso" \
  --project "payments-platform" \
  --repo "payment-service" \
  --pr-id 123

# Get content of a specific file
python .github/skills/azure-devops-api/scripts/get_pr_diff.py \
  --org "contoso" \
  --project "payments-platform" \
  --repo "payment-service" \
  --pr-id 123 \
  --file "/src/Features/Payments/CreatePayment/CreatePaymentHandler.cs"
```

## Error Handling

Scripts return JSON error objects on failure:

```json
{
  "error": true,
  "status": 401,
  "message": "Unauthorized",
  "details": "..."
}
```

Common errors:

| Error                                           | Cause                              | Solution                        |
| ----------------------------------------------- | ---------------------------------- | ------------------------------- |
| `AZURE_DEVOPS_PAT environment variable not set` | PAT not configured                 | Set the environment variable    |
| `401 Unauthorized`                              | PAT invalid or expired             | Generate a new PAT              |
| `404 Not Found`                                 | Repo, PR, or project doesn't exist | Check names/IDs                 |
| `403 Forbidden`                                 | PAT lacks required scope           | Add required permissions to PAT |

## When to Use These Scripts vs MCP

| Need                                   | Use                                          |
| -------------------------------------- | -------------------------------------------- |
| PR metadata (title, status, reviewers) | MCP or scripts                               |
| List of changed files in PR            | Scripts (`get_pr_diff.py`)                   |
| Actual file diffs/content              | Scripts (`get_pr_diff.py --include-content`) |
| PRs filtered by team reviewer          | Scripts (`get_team_prs.py`)                  |
| Work item details                      | MCP                                          |
| Pipeline status                        | MCP                                          |
| Creating/updating work items           | MCP                                          |
| Creating/updating PRs                  | MCP                                          |

**Rule of thumb:** Use the MCP for writes and basic queries. Use these scripts when you need PR diffs or team-filtered PR lists.
