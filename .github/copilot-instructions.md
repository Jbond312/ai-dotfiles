# Copilot Instructions

.NET 9 banking application using Azure DevOps for work items and CI/CD.

## Shell Compatibility

Use `dotnet` and `git` commands — they work identically across all shells. For file operations, use your `search` and `read` tools instead of shell-specific commands.

## Pattern-Specific Instructions

Additional instructions auto-apply based on file type:

- `instructions/csharp.instructions.md` → All `.cs` files
- `instructions/tests.instructions.md` → Test files

## Branch Naming

Format: `backlog/{workitem_id}-{short-description}`

Refer to `azure-devops-workflow` skill for full conventions.

## Commit Messages

Conventional Commits format. Refer to `git-committing` skill.

## Agent Workflow

Custom agents guide development:

1. **Orchestrator** → Detect pipeline state, route to correct agent
2. **Work Item Pickup** → Assign, branch, summarise
3. **Planner** → Create `.planning/PLAN.md`
4. **Coder** → Implement (TDD, One-shot, Bug-fix, Hotfix, Refactoring, Chore)
5. **Reviewer** → Review before commit
6. **Committer** → Commit, create PR, link work item

Plans in `.planning/` should be gitignored.

## Azure DevOps MCP

Use batch tools for multiple updates. Present results in markdown tables.

For team-filtered PRs or sprint board queries, use `azure-devops-api` skill scripts.
