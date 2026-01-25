---
name: azure-devops-workflow
description: "Work item states, transitions, branch naming, and linking conventions for Azure DevOps. Use when picking up work items, updating states, creating branches, or linking PRs."
---

# Azure DevOps Workflow

## Work Item Types

| Type                           | Purpose                       |
| ------------------------------ | ----------------------------- |
| **Product Backlog Item (PBI)** | Deliverable feature or change |
| **Spike**                      | Time-boxed investigation      |

Both follow the same workflow states.

## Work Item States

```
New → Ready → In Progress → Awaiting Merge → Merged → Done
                  ↓
              Blocked
```

| State              | Description          | Assignment       |
| ------------------ | -------------------- | ---------------- |
| **New**            | Not yet refined      | Unassigned       |
| **Ready**          | Available to pick up | Unassigned       |
| **In Progress**    | Actively worked on   | Assigned         |
| **Blocked**        | External dependency  | Remains assigned |
| **Awaiting Merge** | PR created           | Remains assigned |
| **Merged**         | PR merged            | Remains assigned |
| **Done**           | Released             | Remains assigned |

## Valid Transitions

**Picking up:** `Ready` → `In Progress` (normal), `New` → `In Progress` (unusual), `Blocked` → `In Progress` (resuming)

**During development:** `In Progress` → `Blocked`, `In Progress` → `Awaiting Merge`

**Cannot pick up:** Items in `Awaiting Merge`, `Merged`, or `Done`

## Branch Naming

Format: `backlog/{workitem_id}-{short-description}`

- Lowercase, hyphen-separated, 3-5 words
- Remove repository hints: `[interest_accrual] Add X` → `backlog/12345-add-x`

## Repository Hints

Work item titles may include `[repository_name]` prefix. Verify current working directory matches before starting.

## Predecessor Validation

Before picking up, check Predecessor links. Warn if any predecessor is not in `Merged` or `Done`:

```
⚠️ Incomplete predecessors:
| ID | Title | State | Assigned To |
```

## PR Linking

Link using `AB#12345` or full URL. Creates bidirectional link.

## Default Branch

Check for `main` first, fall back to `master`:

```bash
git fetch origin
git rev-parse --verify origin/main >/dev/null 2>&1 && DEFAULT="main" || DEFAULT="master"
git checkout $DEFAULT && git pull origin $DEFAULT
git checkout -b backlog/{id}-{description}
```

## MCP Domains

- `core` — Project/team info
- `work` — Iterations, backlogs
- `work-items` — Work item CRUD
- `repositories` — Git, branches, PRs

Use batch tools for multiple updates.
