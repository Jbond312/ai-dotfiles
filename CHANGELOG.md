# Changelog

All notable changes to the GitHub Copilot agent configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2025-01-25

### Changed

- **what-next agent:**
  - PRs now show "Draft" or "Ready" status in output table
  - Available work items limited to first 5 (with total count shown)
  - Removed MCP from tools (uses scripts exclusively for queries)
- **work-item-pickup agent:**
  - Now explicitly blocks on incomplete predecessors instead of just warning
  - Requires user confirmation before assigning work item
  - Does not offer to plan implementation until user confirms pickup

### Removed

- **pipeline-investigator agent** — Removed as it didn't provide enough value yet

## [0.3.0] - 2025-01-25

### Changed

- **Split context configuration into two files:**
  - `team-context.md` (in `.github/`) — Shared Azure DevOps settings (org, project, team name, team ID, user ID)
  - `project-context.md` (repo root) — Repo-specific settings (architecture, external dependencies, key directories)
- Updated all agents and skills to reference the appropriate context file
- This enables sharing `.github/` across multiple repositories while keeping repo-specific config separate

### Fixed

- Agents now look for `project-context.md` at repo root instead of inside `.github/`

## [0.2.0] - 2025-01-25

### Added

- Pattern-specific instruction files using `applyTo` for targeted context loading:
  - `instructions/csharp.instructions.md` — C# conventions for all `.cs` files
  - `instructions/tests.instructions.md` — Testing conventions for test files
  - `instructions/banking.instructions.md` — Banking domain constraints for production code
- Three new skills extracted from agents:
  - `git-committing` — Conventional commit message format and examples
  - `dotnet-testing` — Test discovery, execution, and baseline verification
  - `code-reviewing` — Review checklist, issue categorisation, external dependency flagging
- Progressive disclosure for VSA skill with reference files:
  - `reference/slice-components.md` — Detailed code examples
  - `reference/code-review-checklist.md` — VSA-specific review criteria

### Changed

- **68% reduction in agent line count** (2,451 → 775 lines) by:
  - Removing explanations of concepts Claude already knows (TDD, git basics, integration tests)
  - Extracting reusable content into skills
  - Referencing skills instead of duplicating content
- **62% reduction in main instructions** (182 → 40 lines) by moving domain-specific content to pattern-matched instruction files
- All agents now reference skills for detailed guidance rather than embedding it
- VSA skill split into overview (71 lines) plus reference files for on-demand loading

### Removed

- Duplicate commit message format (was in both `committer.agent.md` and `copilot-instructions.md`)
- Duplicate banking constraints (was in both agents and instructions)
- Duplicate testing patterns (was in both coder agents)
- Verbose concept explanations throughout all agents

## [0.1.0] - 2025-01-25

### Added

- Initial agent workflow for Azure DevOps work item to PR pipeline:
  - `what-next.agent.md` — Shows available work, PRs needing review, in-progress items
  - `work-item-pickup.agent.md` — Assigns work item, creates branch, summarises scope
  - `planner.agent.md` — Creates implementation plan in `.planning/PLAN.md`
  - `tdd-coder.agent.md` — Implements checklist items iteratively with test-first approach
  - `one-shot-coder.agent.md` — Implements all items in single pass
  - `reviewer.agent.md` — Reviews code before commit, flags external dependencies
  - `committer.agent.md` — Commits with conventional commit messages, updates plan
  - `pr-creator.agent.md` — Creates draft PR linked to work item
  - `pipeline-investigator.agent.md` — Investigates CI/CD failures
- Skills for reusable knowledge:
  - `azure-devops-workflow` — Work item states, transitions, branch naming
  - `azure-devops-api` — Python scripts for team-filtered queries (workaround for MCP limitations)
  - `vertical-slice-architecture` — VSA patterns with Clean Architecture layers
- Global configuration:
  - `copilot-instructions.md` — Project-wide coding standards and workflow overview
  - `project-context.md` — Repository-specific configuration template
- Python scripts for Azure DevOps API:
  - `get_sprint_work_items.py` — Query current sprint with Area Path filtering
  - `get_team_prs.py` — Get PRs where team is assigned as reviewer
