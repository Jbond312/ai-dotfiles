# Changelog

All notable changes to the GitHub Copilot agent configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.7.0] - 2025-01-27

### Fixed
- **Handoff agent references** now use the correct `name` field (e.g., `TDD Coder`) instead of filename (e.g., `tdd-coder`)
- **Removed stale handoff** in PR Creator that referenced the deleted `pipeline-investigator` agent

### Changed
- **Handoffs now auto-send by default** (`send: true`) for seamless workflow progression
  - Exceptions: `What Next → Work Item Pickup` and `Reviewer → TDD Coder` remain `send: false` (require user decision)
- **repo-analyzer skill completely rewritten** with discovery-focused approach:
  - Now explores and documents what patterns exist rather than looking for specific frameworks
  - Structured discovery of: Architecture pattern, .NET version, external dependencies, testing approach, code patterns, code style
  - Includes "For Agents" section summarising key guidance
  - Handles unclear/mixed patterns gracefully
- **Planner agent** now has explicit "Step 0" that verifies CONVENTIONS.md exists before planning
- **Build verification** made more explicit in both coder agents — must run `dotnet build` and `dotnet test` before handoff

## [0.6.0] - 2025-01-26

### Added
- **repo-analyzer skill** — Discovers coding conventions from existing codebase and generates `.planning/CONVENTIONS.md`:
  - Test framework and naming patterns
  - Handler/mediator patterns (MediatR, custom, direct services)
  - Mapping approach (AutoMapper, Mapster, static methods)
  - Error handling style (Result pattern, exceptions)
  - Code style preferences (nullability, namespaces, records)
  
- **csharp-coding skill** — C# coding standards with Must/Must Not rules:
  - Hard rules: Explicit null handling, DI patterns, input validation
  - Must Not: DateTime.Now, swallowing exceptions, magic strings, service locator
  - Golden examples: Constructor injection, Result pattern, guard clauses
  - Anti-patterns with explanations of why they're problematic
  - Banking-specific rules: decimal for money, idempotency, audit trails

- **Verification checklist in PLAN.md** — Tracks TDD compliance and quality gates:
  - Before Implementation: baseline passes, branch created, conventions reviewed
  - Per Item: RED/GREEN/REFACTOR phases, no new warnings
  - Before PR: all tests pass, follows conventions, external dependencies flagged

- **Automatic gitignore management** — Agents ensure `.vscode/` and `.planning/` are gitignored:
  - Checked during work-item-pickup and planner phases
  - Prevents accidental commit of local settings and PATs

### Changed
- **dotnet-testing skill significantly enriched:**
  - Complete TDD workflow (RED → GREEN → REFACTOR) with commands
  - Golden examples for test structure, naming patterns, parameterised tests
  - Anti-patterns: testing implementation details, non-deterministic tests, over-mocking
  - Must/Must Not rules for test quality

- **code-reviewing skill enriched:**
  - Good vs Bad code examples with explanations
  - Null handling, error handling, idempotency, logging examples
  - External dependency flag template with verification checklist
  - Review report format includes PLAN.md verification status

- **planner agent** now:
  - Checks for `.planning/CONVENTIONS.md` before planning
  - References conventions for test naming and patterns
  - Generates verification checklist in plan
  - Ensures `.vscode/` and `.planning/` are gitignored

- **work-item-pickup agent** now:
  - Checks if conventions file exists before handoff to planner
  - Offers to run repo-analyzer if conventions missing
  - Ensures `.vscode/` and `.planning/` are gitignored

- **reviewer agent** now:
  - Verifies against CONVENTIONS.md patterns
  - Checks PLAN.md verification checklist completion
  - Updates verification status in review report

- **tdd-coder agent** now:
  - Reads CONVENTIONS.md for naming and patterns
  - Updates verification checklist during TDD cycle
  - References csharp-coding and dotnet-testing skills

### Philosophy
This release follows the "Must / Must Not / Golden Example" pattern from community best practices:
- Skills now contain detailed instructions, not just triggers
- Convention discovery ensures portability across repositories
- Verification checklists provide concrete quality gates

## [0.5.0] - 2025-01-26

### Changed
- **Azure DevOps configuration now uses environment variables** instead of team-context.md:
  - `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_TEAM`
  - Optional: `AZURE_DEVOPS_TEAM_ID`, `AZURE_DEVOPS_USER_ID`
  - Configure in `.vscode/settings.json` under `terminal.integrated.env.*`
- **Python scripts simplified** — no longer require `--org`, `--project`, `--team` arguments
- **Improved skill descriptions** with explicit trigger phrases for better automatic discovery:
  - Added "Triggers on:" keywords to all skill descriptions
  - Added "Use when asked to..." phrases matching common user prompts

### Removed
- **team-context.md** — replaced by environment variables

### Fixed
- Agents should now be more reliable as configuration comes from environment variables rather than requiring file parsing

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
