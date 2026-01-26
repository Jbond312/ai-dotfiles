# Copilot Instructions

.NET 9 banking application using Azure DevOps for work items and CI/CD.

## Pattern-Specific Instructions

Additional instructions auto-apply based on file type:
- `instructions/csharp.instructions.md` → All `.cs` files
- `instructions/tests.instructions.md` → Test files
- `instructions/banking.instructions.md` → Features, Domain, Infrastructure

## Branch Naming

Format: `backlog/{workitem_id}-{short-description}`

Refer to `azure-devops-workflow` skill for full conventions.

## Commit Messages

Conventional Commits format. Refer to `git-committing` skill.

## Agent Workflow

Custom agents guide development:

1. **What Next** → Show options
2. **Work Item Pickup** → Assign, branch, summarise
3. **Planner** → Create `.planning/PLAN.md`
4. **Coder** → Implement (TDD or one-shot)
5. **Reviewer** → Review before commit
6. **Committer** → Commit with message
7. **PR Creator** → Draft PR, link work item

Plans in `.planning/` should be gitignored.

## Azure DevOps MCP

Use batch tools for multiple updates. Present results in markdown tables.

For team-filtered PRs or sprint board queries, use `azure-devops-api` skill scripts.
