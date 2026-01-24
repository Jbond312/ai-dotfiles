---
name: azure-devops-workflow
description: "Work item states, transitions, branch naming, and linking conventions for Azure DevOps. Use when picking up work items, updating states, creating branches, or linking PRs to work items."
---

# Azure DevOps Workflow

This skill documents our Azure DevOps board configuration, work item lifecycle, and conventions for branches and linking.

## Work Item Types

We use two work item types:

| Type                           | Purpose                                           |
| ------------------------------ | ------------------------------------------------- |
| **Product Backlog Item (PBI)** | Deliverable feature or change with business value |
| **Spike**                      | Time-boxed investigation or research task         |

Both follow the same workflow states and conventions.

## Work Item States

```
┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌─────────────────┐     ┌────────┐     ┌──────┐
│   New   │ ──▶ │  Ready  │ ──▶ │ In Progress │ ──▶ │ Awaiting Merge  │ ──▶ │ Merged │ ──▶ │ Done │
└─────────┘     └─────────┘     └─────────────┘     └─────────────────┘     └────────┘     └──────┘
                                       │
                                       ▼
                                 ┌─────────┐
                                 │ Blocked │
                                 └─────────┘
```

### State Definitions

| State              | Description                                                                       | Assignment           |
| ------------------ | --------------------------------------------------------------------------------- | -------------------- |
| **New**            | Work item created but not yet refined or estimated. Unusual to pick up from here. | Unassigned           |
| **Ready**          | Refined, estimated, and available for any engineer to pick up.                    | Unassigned           |
| **In Progress**    | Actively being worked on. Branch created, coding underway.                        | Assigned to engineer |
| **Blocked**        | Work cannot continue due to external dependency or issue.                         | Remains assigned     |
| **Awaiting Merge** | PR created and awaiting review. Code complete.                                    | Remains assigned     |
| **Merged**         | PR merged, awaiting release to production.                                        | Remains assigned     |
| **Done**           | Released to production. Work complete.                                            | Remains assigned     |

### Valid State Transitions

**Picking up work:**

- `New` → `In Progress` (unusual but allowed)
- `Ready` → `In Progress` (normal flow)
- `Blocked` → `In Progress` (resuming after unblock)

**During development:**

- `In Progress` → `Blocked` (only when explicitly requested)
- `In Progress` → `Awaiting Merge` (when PR is created)

**After PR:**

- `Awaiting Merge` → `Merged` (when PR is merged)
- `Merged` → `Done` (when released to production)

**Invalid transitions:**

- Cannot pick up items in `Awaiting Merge`, `Merged`, or `Done`
- Cannot move directly from `New` or `Ready` to `Awaiting Merge`

## Branch Naming Convention

All feature branches follow this format:

```
backlog/{workitem_id}-{short-description}
```

**Rules:**

- `{workitem_id}` is the Azure DevOps work item ID (numeric)
- `{short-description}` is derived from the work item title
- Lowercase, hyphen-separated
- 3-5 words maximum
- Remove any repository hints in square brackets from the title

**Examples:**

| Work Item Title                                    | Branch Name                                          |
| -------------------------------------------------- | ---------------------------------------------------- |
| Add payment validation for international transfers | `backlog/12345-add-payment-validation-international` |
| [interest_accrual] Add Quarterly Payable Period    | `backlog/12346-add-quarterly-payable-period`         |
| Fix race condition in account balance calculation  | `backlog/12347-fix-race-condition-balance-calc`      |

## Repository Hints

Work item titles may include a repository hint in square brackets:

```
[repository_name] Work item title
```

**Examples:**

- `[interest_accrual] Add Quarterly Payable Period`
- `[payments-api] Fix timeout on large batches`

**Purpose:**

- Indicates which repository the change should be made in
- Helps developers ensure they're in the correct repo before starting
- Should be removed when deriving branch names or PR titles

**Validation:**
When picking up a work item with a repository hint, verify the current working directory matches the hinted repository. Warn if they don't match.

## Work Item Links

### Link Types

| Link Type       | Description                               | Direction          |
| --------------- | ----------------------------------------- | ------------------ |
| **Parent**      | Links to parent Epic or Feature           | Child → Parent     |
| **Predecessor** | Work that must complete before this item  | Blocked → Blocking |
| **Successor**   | Work that depends on this item completing | Blocking → Blocked |
| **Related**     | General association without dependency    | Bidirectional      |

### Predecessor Validation

Before picking up a work item, check for Predecessor links:

1. Fetch all linked items with type `Predecessor`
2. Check each predecessor's state
3. If any predecessor is **not** in `Merged` or `Done`, warn the developer

**Warning format:**

```
⚠️ This work item has incomplete predecessors:

| ID | Title | State | Assigned To |
|----|-------|-------|-------------|
| #123 | Predecessor title | In Progress | Jane Smith |

Proceeding may result in merge conflicts or wasted effort.
```

The developer can choose to:

- View predecessor details
- Proceed anyway (not recommended)
- Pick up the predecessor instead

### PR Linking

When creating a pull request, link it to the work item using:

- Azure DevOps syntax: `AB#12345`
- Or full URL: `https://dev.azure.com/{org}/{project}/_workitems/edit/12345`

This creates a bidirectional link visible in both the PR and the work item.

## Default Branch

Repositories may use either `main` or `master` as the default branch. When creating feature branches:

1. Check for `main` first: `git rev-parse --verify origin/main`
2. Fall back to `master` if `main` doesn't exist
3. Always branch from the default branch with latest changes

```bash
git fetch origin
git rev-parse --verify origin/main >/dev/null 2>&1 && DEFAULT_BRANCH="main" || DEFAULT_BRANCH="master"
git checkout $DEFAULT_BRANCH
git pull origin $DEFAULT_BRANCH
git checkout -b backlog/{id}-{description}
```

## Assignment Rules

| State          | Assignment Rule                                |
| -------------- | ---------------------------------------------- |
| New            | Must be unassigned                             |
| Ready          | Must be unassigned                             |
| In Progress    | Must be assigned to the engineer working on it |
| Blocked        | Remains assigned to the original engineer      |
| Awaiting Merge | Remains assigned                               |
| Merged         | Remains assigned                               |
| Done           | Remains assigned                               |

**Important:** Do not pick up work items that are `In Progress` and assigned to someone else. Coordinate with the current assignee first.

## MCP Tools Reference

When interacting with Azure DevOps via the MCP server, use these domains:

- `core` — Project and team information
- `work` — Iterations, backlogs, team settings
- `work-items` — Work item CRUD operations
- `repositories` — Git repositories, branches, PRs

**Best practices:**

- Use batch tools for multiple updates instead of individual calls
- Fetch work item IDs first, then use `get_work_items_batch_by_ids` for details
- Present work item results in markdown tables with columns: ID, Type, Title, State
