# Changelog

All notable changes to the GitHub Copilot agent configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.12.0] - 2026-02-05

### Added

- **`mssql-stored-procedures` skill** — MSSQL stored procedure development standards for banking applications. Covers schema design, the Sommarskog error handling pattern, performance (SARGability, parameter sniffing, set-based operations, temp tables vs table variables, isolation levels), security (injection prevention, least privilege), and banking domain (DECIMAL precision, idempotency, concurrency control, temporal tables, double-entry accounting). Includes good/bad code examples and review checklist.

- **`tsqlt-testing` skill** — tSQLt unit testing standards for SQL Server stored procedures. Covers test structure and naming, core features (FakeTable, SpyProcedure, ExpectException, FakeFunction, ApplyConstraint, ApplyTrigger), what to test vs what not to test, test data patterns (minimal data, factories, determinism), and common pitfalls (identity loss, transaction rollback, temp tables, schema-bound views, cross-database, concurrency). Includes good/bad examples and review checklist.

- **SQL sections in `known-issues` skill** — Placeholder sections for "SQL & Stored Procedures" and "tSQLt Testing" with example formats.

- **Build & test gates on Committer and PR Creator** — Both agents now run `dotnet build` and `dotnet test` as hard blockers before proceeding. The Committer verifies after committing (catches post-review regressions); the PR Creator verifies before pushing (last line of defence before code reaches the team).

- **Universal build/test failure rule in `quality-gates` skill** — "A failing build or failing tests is never 'unrelated to our changes.' The workflow stops until it's fixed — no exceptions." Codifies the principle that we never advance work on a broken codebase.

### Changed

- **TDD session-per-item architecture** — The Committer no longer hands off to the TDD Coder. Instead, after each commit it instructs the user to start a new chat session. The Orchestrator picks up from PLAN.md state and routes to the next item with a fresh context window. This prevents quality degradation from context accumulation across items (research shows 20-30% performance loss with accumulated context).

- **Verification-only TDD items** — The Committer now handles items that produce no code changes (confirming existing behaviour, checking execution plans, validating configurations). It skips commit steps and proceeds directly to plan updates and the "start new session" message.

- **Quiet verbosity at gate checkpoints** — Reviewer, Committer, PR Creator, PR Reviewer, and Planner now use `-v q` (quiet) for build and test commands. Errors and failures still appear, but successful build/test noise is suppressed — significantly reducing context window consumption. Implementation agents (TDD Coder, One-Shot Coder, Debug, Implementation Verifier) retain default/normal verbosity for diagnostic detail. On failure at a gate, agents re-run without `-v q` for full output.

- **Reviewer runs build before tests** — The Reviewer now runs `dotnet build` before `dotnet test`, with stronger wording: "do not approve if either fails, regardless of whether the failures appear related to the current changes."

- **Reviewer and PR Reviewer reference new SQL skills** — Both agents now include `mssql-stored-procedures` and `tsqlt-testing` skill checklists for `.sql` file changes and SQL test changes respectively.

### Why These Changes?

**SQL skills:** Banking applications have significant stored procedure codebases. The new skills provide the same depth of guidance for SQL development and testing that `code-reviewing` and `security-review` provide for .NET — including banking-specific concerns like DECIMAL precision, idempotency, and temporal tables for audit trails.

**Session-per-item TDD:** VS Code Copilot has no `/compact` command. The only way to get a fresh context window is a new chat session. Research (Anthropic's multi-session harness pattern, Chroma's context rot study) shows monotonic quality degradation as context grows. The file-based state design (PLAN.md) already supports session breaks — this change makes the workflow explicitly leverage it.

**Quiet verbosity:** Build and test output is the #1 context consumer, run 6+ times across agents in a single item's lifecycle. Gate checks only need pass/fail — the detailed output is wasted context. Using `-v q` at gates while preserving detail in implementation agents gives the best of both: lean gates and rich diagnostics where they're needed.

**Build/test gates everywhere:** Prevents the AI from dismissing failures as "unrelated to our changes" — a pattern observed in practice. Every handoff point now enforces green builds as a hard blocker.

## [0.11.0] - 2025-02-05

### Added

- **`agents` arrays in YAML frontmatter** — Agents that invoke subagents (Work Item Pickup, Planner, TDD Coder, One-Shot Coder, Spike) now declare their subagent targets via the `agents` property. This restricts which agents can be called via the `agent` tool at the platform level. Handoffs are separately constrained by the `handoffs` section.

- **`user-invokable: false` for subagent-only agents** — Repo Analyser and Implementation Verifier are now hidden from the agents dropdown since they are only invoked programmatically by other agents. Reduces visible agents from 12 to 10.

### Changed

- **VS Code 1.109.0+ now required** — The `agents` and `user-invokable` frontmatter properties require VS Code 1.109.0 or later. Updated prerequisites and team rollout checklist in DEVELOPER_SETUP.md.

- **New setup step: `chat.customAgentInSubagent.enabled`** — Added as step 3 in DEVELOPER_SETUP.md. Required for agents to invoke other agents as subagents.

### Why These Changes?

Subagent invocations were previously unconstrained — any agent with the `agent` tool could invoke any other agent. Adding `agents` arrays restricts this at the platform level so each agent can only invoke its intended subagents. Handoffs remain separately constrained by the `handoffs` section. Combined with `user-invokable: false`, this gives tighter control over the workflow topology and a cleaner user-facing agents dropdown.

## [0.10.0] - 2025-02-04

### Removed

- **`project-context.md` template** — Deleted entirely. All useful content (architecture pattern, framework version, key directories, dependencies, conventions) is already auto-discovered by the Repo Analyser and documented in `.planning/CONVENTIONS.md`. Agents now reference CONVENTIONS.md directly. Eliminates manual maintenance and drift risk.

- **`vertical-slice-architecture` skill** — Deleted entirely. Architecture is now a discovered property, not a hardcoded skill. The Repo Analyser already identifies architecture patterns (VSA, Clean, Hexagonal, N-Tier) and documents them in CONVENTIONS.md. Agents now read from CONVENTIONS.md instead of referencing a specific skill.

### Changed

- **Agent architecture references genericised** — Planner, TDD Coder, One-Shot Coder, and Reviewer agents now reference CONVENTIONS.md for architectural patterns instead of the deleted VSA skill.
- **Agent `project-context.md` references removed** — Planner, TDD Coder, One-Shot Coder, and PR Creator agents now reference `.planning/CONVENTIONS.md` directly. PR Creator reviewer assignment changed from "Team from project-context.md" to "Assign appropriate team reviewers".
- **`DEVELOPER_SETUP.md` updated** — Removed `project-context.md` from directory tree, file locations table, and team rollout checklist. Removed "Configure Project Context" setup section.
- **`WORKFLOW.md` updated** — Removed all `project-context.md` references from walkthrough phases, files read lists, file artifacts table, and PR Creator section.

### Why This Change?

Architecture should be discovered, not assumed. The Repo Analyser already handles this — it identifies the architecture pattern during convention discovery and documents it in CONVENTIONS.md. Having a separate hardcoded VSA skill created a false dependency and limited the workflow to a single architecture style.

## [0.9.0] - 2025-02-04

### Added

- **WORKFLOW.md walkthrough document** — Narrative walkthrough of the complete agent workflow using a concrete "Add payment validation" scenario. Covers every phase from Orchestrator entry through PR creation, including alternate paths (One-Shot, Spike, Debug, Changes Requested, Context Loss Recovery). Includes Mermaid flow diagram, skills reference table, file artifacts table, and observations on gaps and trade-offs.

- **Retrospective feedback loop in Committer agent** — Prompts "anything to record in known-issues?" after all checklist items are complete (final commit only). Skipped for intermediate TDD commits. Zero-friction opt-out: say "nothing" and move on immediately.

- **Retrospective check in Orchestrator agent** — When returning to main with no plan, checks `git log` for recently completed work and offers the same known-issues prompt before showing work options. Skipped when git log shows no recent activity.

- **Orchestrator gains `edit` tool** — Narrowly scoped to allow writing known-issues entries from the retrospective prompt.

### Changed

- **Quality gates at agent handoffs** — Structured self-checks at three handoff points (Planner→Coder, Coder→Reviewer, Reviewer→Committer). New `quality-gates` skill defines centralised criteria. PASS/WARN format — flags concerns without hard-blocking (existing hard blocks unchanged). Implementation Verifier now collects code coverage via `--collect:"XPlat Code Coverage"` (best-effort, works without coverlet).

- **Plan checklist items checked off earlier** — Coders now mark items complete during implementation (not batched at the end). One-Shot Coder checks off each item as it's completed. Committer no longer redundantly re-checks items — only updates Work In Progress status.

- **Planner checklist item cap softened** — Hard cap of 8 items replaced with "aim for 3-6, suggest splitting if approaching 10". Allows flexibility for legitimately larger work items.

### Why These Changes?

Captures gotchas and learnings at natural completion points — right after finishing work (Committer) and right before starting new work (Orchestrator). Feeds directly into the known-issues skill so future cycles avoid the same mistakes. Designed to be zero-friction: one question, instant skip if nothing to report.

## [0.8.0] - 2025-01-29

### Added

- **Implementation Verifier agent** (`implementation-verifier.agent.md`) — Subagent that verifies implementation completeness:
  - Compares implemented code against PLAN.md checklist
  - Checks each item has corresponding code and tests
  - Runs build and test verification
  - Returns structured report with recommendations

- **Clarification Phase in Planner** — Interactive questioning before finalising plans:
  - Presents understanding summary with scope assumptions
  - Asks clarifying questions about: edge cases, error handling, banking requirements, integrations
  - Documents answers in the plan for coder context

- **Examples folders for skills** — Following Agent Skills standard:
  - `csharp-coding/examples/` — service-with-di.cs, result-pattern.cs, handler-pattern.cs

### Changed

- **Tool renamed from `runSubagent` to `agent`** — Updated all agents to use correct tool name
- **Stronger subagent instructions** — Explicit "you MUST use the `agent` tool, do NOT do this yourself" language
- **Planner simplified** — Removed redundant Verification Checklist (now handled by Implementation Verifier)
- **Planner adds "Clarifications Received" section** — Documents user answers for coder context
- **Coder agents use Implementation Verifier** before handoff:
  - One-Shot Coder: Verifies before every handoff
  - TDD Coder: Verifies after final item only
- **Todo list encouragement** — Coders now prompted to create todo lists for tracking progress
- **Skills aligned with Agent Skills standard**:
  - Added `## When to Use This Skill` sections
  - Cleaner structure following agentskills.io conventions
  - Removed verbose trigger keywords from descriptions

### Why These Changes?

**Clarification Phase:** Surfaces ambiguity early, builds shared understanding, gives the AI more context for better code.

**Implementation Verifier:** Catches gaps before human review. The coder might think it's done but miss edge cases or tests.

**Agent Skills Standard:** Makes skills portable across VS Code, Copilot CLI, and Copilot coding agent. Cleaner structure improves discoverability.

## [0.7.0] - 2025-01-28

### Added
- **Repo Analyser agent** (`repo-analyser.agent.md`) — Dedicated agent for repository analysis, designed to be invoked as a subagent
- **Subagent support** — Work Item Pickup and Planner now use `agent` tool to invoke Repo Analyser in an isolated context

### Fixed
- **Handoff agent references** now use the correct `name` field (e.g., `TDD Coder`) instead of filename (e.g., `tdd-coder`)
- **Removed stale handoff** in PR Creator that referenced the deleted `pipeline-investigator` agent
- **British spelling** — Renamed `repo-analyzer` to `repo-analyser` throughout

### Changed
- **Handoffs now auto-send by default** (`send: true`) for seamless workflow progression
  - Exceptions: `What Next → Work Item Pickup` and `Reviewer → TDD Coder` remain `send: false` (require user decision)
- **repo-analyser skill rewritten** with discovery-focused approach:
  - Now explores and documents what patterns exist rather than looking for specific frameworks
  - Structured discovery of: Architecture pattern, .NET version, external dependencies, testing approach, code patterns, code style
  - Includes "For Agents" section summarising key guidance
  - Handles unclear/mixed patterns gracefully
- **Planner agent** now has explicit "Step 0" that verifies CONVENTIONS.md exists before planning
- **Build verification** made more explicit in both coder agents — must run `dotnet build` and `dotnet test` before handoff

### Why Subagents?

The Repo Analyser runs many file searches and examinations that would otherwise pollute the main agent's context window. By running as a subagent:
- The analysis context is discarded after completion
- Only the summary is returned to the main conversation
- The main agent stays focused on its primary task

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
