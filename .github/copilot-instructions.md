# Copilot Instructions

.NET 9 banking application using Azure DevOps for work items and CI/CD.

## Shell Compatibility

Team members use different shells (PowerShell, bash, zsh, cmd). When executing terminal commands:

1. **Detect the user's shell** from the terminal context and adapt syntax accordingly
2. **Prefer cross-platform commands** where they exist:
   - `dotnet` CLI commands work identically everywhere
   - `git` commands work identically everywhere
   - File operations vary — adapt `mkdir`, `test -f`, `find` etc. to the user's shell
3. **Focus on intent over syntax** — if instructions say "check if file exists", use the appropriate method for the current shell

Common adaptations:

| Intent            | Bash                  | PowerShell                                 |
| ----------------- | --------------------- | ------------------------------------------ |
| Check file exists | `test -f path`        | `Test-Path path`                           |
| Create directory  | `mkdir -p path`       | `New-Item -ItemType Directory -Force path` |
| Find files        | `find . -name "*.cs"` | `Get-ChildItem -Recurse -Filter *.cs`      |
| Check in git      | `git ls-files "*.cs"` | `git ls-files "*.cs"` (same)               |

When in doubt, use `dotnet` and `git` commands — they're consistent across all platforms.

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
