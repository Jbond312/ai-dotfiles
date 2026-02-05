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

**On failure:** Fix the plan before offering handoff.

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

## Gate: Reviewer → Committer

After review completes:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | No critical issues | Zero Critical severity findings (hard block) |
| 2 | No security blockers | Zero Critical security findings (hard block) |
| 3 | Important issues addressed | Fixed or explicitly accepted |
| 4 | External deps flagged | New external dependencies documented |
| 5 | Tests pass | `dotnet test` exit code 0 (hard block) |

Criteria 1-2, 5 are hard blocks. Criteria 3-4 are soft (WARN if unmet).
