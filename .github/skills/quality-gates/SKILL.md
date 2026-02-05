---
name: quality-gates
description: "Quality gate criteria for agent handoffs. Defines what each agent must verify before handing off to the next."
---

# Quality Gates

Structured checks at each handoff point. Agents report gate status using the summary format below.

## When to Use This Skill

Reference the relevant gate section before handing off to the next agent.

## Gate Summary Format

```markdown
## Quality Gate: {PASS | WARN}

- {Criterion}: {PASS | WARN — reason}
```

**PASS** — all criteria met. **WARN** — one or more soft criteria unmet (note which).
Never hard-block on WARN — flag and proceed. Existing hard blocks (build fails, tests fail) are unchanged.

## Gate: Planner → Coder

After saving PLAN.md, verify:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | Test coverage in plan | Every checklist item has ≥1 test scenario |
| 2 | External Dependencies | Section exists (even if "None") |
| 3 | Assumptions & Risks | Section exists |
| 4 | Clarifications documented | "Clarifications Received" section has content |
| 5 | Item structure | Each item has What, How, Files, and Done criteria |
| 6 | Item count | Between 3 and 10 items |
| 7 | Scope defined | Scope section has Includes and Excludes |
| 8 | Decision Log section | Section exists (can be empty — populated during implementation) |
| 9 | Progress header | `**Progress:** 0/{N} items` present with correct count |

**On failure:** Fix the plan before offering handoff.

### Workflow-Specific Adjustments

**Bug-fix:** Criteria 1 becomes "Reproduction steps documented" and add "Root cause hypothesis exists". Criterion 4 (clarifications) focuses on reproduction environment and observed vs expected behaviour.

**Refactoring:** Add criterion "Behaviour preservation statement exists in Summary". Criterion 1 becomes "Safety checks documented per item" (existing tests that must remain green, not new test scenarios).

**Chore:** Criterion 6 (item count) minimum lowered to 1. Criteria 1 (test scenarios) and 4 (clarifications) are optional — skip if genuinely unnecessary. Criterion 7 (scope) is optional.

## Gate: Coder → Reviewer

After Implementation Verifier runs:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | Build passes | `dotnet build` exit code 0 (hard block) |
| 2 | All tests pass | `dotnet test` exit code 0 (hard block) |
| 3 | Plan items addressed | Verifier reports no ❌ items |
| 4 | Plan items have tests | Verifier reports no missing tests |
| 5 | Coverage collected | Report line coverage % if available |

Criteria 1-2 are hard blocks. Criteria 3-5 are soft (WARN if gaps).

### Workflow-Specific Adjustments

**Bug-fix:** Add criterion "Regression test exists" (hard block — a bug fix without a regression test is incomplete). Criterion 4 checks regression test, not general test coverage.

**Refactoring:** Criterion 4 becomes "Existing tests pass unchanged" — no new tests expected. Criterion 3 checks structural changes match plan items.

**Chore:** Criteria 3-4 (verifier checks) are skipped — chores are too lightweight for verification.

## Gate: Reviewer → Committer

After review completes:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | No critical issues | Zero Critical severity findings (hard block) |
| 2 | No security blockers | Zero Critical security findings (hard block) |
| 3 | Important issues addressed | Fixed or explicitly accepted |
| 4 | External deps flagged | New external dependencies documented |
| 5 | Build passes | `dotnet build` exit code 0 (hard block) |
| 6 | All tests pass | `dotnet test` exit code 0 (hard block) |

Criteria 1-2, 5-6 are hard blocks. Criteria 3-4 are soft (WARN if unmet).

## Gate: Committer → Next Step

After committing (or confirming no changes for verification-only items):

| # | Criterion | Check |
|---|-----------|-------|
| 1 | Build passes | `dotnet build` exit code 0 (hard block) |
| 2 | All tests pass | `dotnet test` exit code 0 (hard block) |

Both are hard blocks. Do not update PLAN.md or proceed to handoff if either fails. Hand back to the coder to fix.

**Rationale:** The Committer is the last gate before code is committed/advanced. Even if the Reviewer verified earlier, changes may have been made after review (feedback fixes, merge conflicts). Never trust that "tests passed earlier" — always verify.

## Gate: PR Creator → Push

Before pushing and creating the PR:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | Build passes | `dotnet build` exit code 0 (hard block) |
| 2 | All tests pass | `dotnet test` exit code 0 (hard block) |

Both are hard blocks. Do not push or create a PR if either fails. This is the last line of defence before code reaches the team.

## Build & Test Failures: Universal Rule

**A failing build or failing tests is never "unrelated to our changes".** If the codebase doesn't compile or tests don't pass, the workflow stops until it's fixed. This applies to every agent at every gate — no exceptions, no "it was already broken" dismissals. We do not advance work on a broken codebase.

**Exception:** Integration tests may be excluded from this rule via the Integration Test Exclusion Protocol (see below). When excluded, "all tests pass" means "all non-integration tests pass".

## Integration Test Exclusion Protocol

Integration tests often depend on external resources (SQL connection strings, message queues, external APIs) that may not be available in every development environment. This protocol allows the workflow to proceed when only integration tests are failing due to environment configuration.

### When This Applies

**Only during baseline verification** (the first test run before any changes are made). This protocol does NOT apply to tests that start failing after code changes — those are always treated as real failures.

### Detection

After running `dotnet test`, if tests fail:

1. **Examine the output** to identify which test projects failed
2. **Check if ALL failures are in integration test projects** — projects whose name contains `IntegrationTests` or `Integration.Tests` (e.g., `MyProject.IntegrationTests`, `MyProject.Integration.Tests`)
3. **If non-integration tests also fail:** STOP. The codebase is broken. Report to developer. Do not apply this protocol.

### User Prompt

If only integration test projects failed, ask:

> Integration tests are failing — this is typically caused by missing connection strings or external service configuration.
>
> **Do you need integration tests for this work?**
>
> 1. **No** — exclude integration tests and proceed (unit tests will still run at every gate)
> 2. **Yes** — please ensure integration tests can execute successfully before we start

### Recording the Decision

**If excluded:** Add the following field to PLAN.md immediately after the `**Progress:**` line:

```markdown
**Integration Tests:** Excluded
```

Then re-run tests excluding integration test projects to confirm the remaining tests pass:

```bash
dotnet test --no-build --filter "FullyQualifiedName!~IntegrationTests & FullyQualifiedName!~Integration.Tests"
```

If the remaining tests also fail, STOP — this is a genuine failure, not an integration test issue.

**If included:** STOP and ask the user to fix integration test configuration before starting. Do not proceed with a failing test suite.

### How Gates Adjust

When `**Integration Tests:** Excluded` is present in PLAN.md, **all agents at all gates** replace:

```bash
dotnet test --no-build
```

with:

```bash
dotnet test --no-build --filter "FullyQualifiedName!~IntegrationTests & FullyQualifiedName!~Integration.Tests"
```

The same applies to quiet-mode gate checks — append the filter:

```bash
dotnet test --no-build -v q --filter "FullyQualifiedName!~IntegrationTests & FullyQualifiedName!~Integration.Tests"
```

And to verification runs with coverage:

```bash
dotnet test --no-build --verbosity normal --collect:"XPlat Code Coverage" --filter "FullyQualifiedName!~IntegrationTests & FullyQualifiedName!~Integration.Tests"
```

**The filter is the same everywhere.** Agents do not need to discover project names — the compound filter excludes any test whose namespace contains "IntegrationTests" or "Integration.Tests", covering both common naming conventions (`MyProject.IntegrationTests` and `MyProject.Integration.Tests`).

## Verbosity Convention

**Gate checks** (Reviewer, Committer, PR Creator, PR Reviewer, Planner) use `-v q` (quiet) to minimise context window usage. Errors and failures still appear in quiet mode — only the success noise is suppressed.

**Implementation agents** (TDD Coder, One-Shot Coder, Bug Fix Coder, Debug, Implementation Verifier) use default or normal verbosity because they need to see test names, assertion details, and coverage data.

**On failure at a gate:** Re-run without `-v q` to get full diagnostic output before handing back to the coder or reporting to the user.
