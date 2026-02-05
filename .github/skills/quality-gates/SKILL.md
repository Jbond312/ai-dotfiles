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

## Verbosity Convention

**Gate checks** (Reviewer, Committer, PR Creator, PR Reviewer, Planner) use `-v q` (quiet) to minimise context window usage. Errors and failures still appear in quiet mode — only the success noise is suppressed.

**Implementation agents** (TDD Coder, One-Shot Coder, Bug Fix Coder, Debug, Implementation Verifier) use default or normal verbosity because they need to see test names, assertion details, and coverage data.

**On failure at a gate:** Re-run without `-v q` to get full diagnostic output before handing back to the coder or reporting to the user.
