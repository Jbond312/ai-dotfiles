---
name: conventional-comments
description: "Format review feedback as conventional comments for Azure DevOps PRs. Use when producing PR review output, formatting review comments, or mapping severity to labels. Triggers on: conventional comments, PR comments, review format, comment format, label decoration."
---

# Conventional Comments

Format for structured, actionable PR review comments. Based on [conventionalcomments.org](https://conventionalcomments.org/).

## Format

```
<label> [decorations]: <subject>

[discussion]
```

## Labels

| Label | Meaning | When to Use |
|-------|---------|-------------|
| `praise` | Highlights good work | Patterns done well, clever solutions, good test coverage |
| `nitpick` | Trivial preference-based suggestion | Naming style, formatting, minor readability — never blocking |
| `suggestion` | Proposes an improvement | Better approach, refactoring opportunity, pattern alignment |
| `issue` | Identifies a problem that must be addressed | Bugs, security flaws, data integrity risks, broken logic |
| `todo` | Small necessary change | Missing null check, absent test, required cleanup |
| `question` | Asks for clarification | Unclear intent, ambiguous logic, missing context |
| `thought` | Shares an idea for consideration | Alternative approaches, future considerations — not actionable now |
| `chore` | Mechanical task needed | Update a config, rename for consistency, remove dead code |
| `note` | Informational context | External dependency flags, environment requirements, FYI items |

## Banking Domain Decorations

| Decoration | Meaning |
|------------|---------|
| `(security)` | Security concern — injection, auth, data exposure |
| `(banking)` | Banking domain concern — idempotency, audit, financial rules |
| `(financial-integrity)` | Financial calculation or data correctness |
| `(audit)` | Audit trail or traceability concern |
| `(pii)` | Personally identifiable information exposure |
| `(performance)` | Performance concern — LINQ traps, N+1, boxing |
| `(test)` | Test quality or coverage concern |

## Severity Mapping

| Severity (code-reviewing) | Label | Decoration | Rationale |
|---------------------------|-------|------------|-----------|
| **Critical** | `issue` | `(blocking)` | Must fix before merge |
| **Important** | `suggestion` or `todo` | varies | `todo` for specific fixes; `suggestion` for approach changes |
| **Suggestion** | `suggestion` or `nitpick` | `(non-blocking)` | `nitpick` for pure style; `suggestion` for meaningful improvements |
| **External** | `note` | `(blocking)` | Requires human verification — always blocking |

Security issues are always: `issue (blocking, security): <subject>`

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Mark style issues as `(blocking)` | Use `nitpick (non-blocking)` for style |
| Write a label with no discussion | Always include at least one sentence explaining *why* |
| Use `issue` for suggestions | Reserve `issue` for actual bugs or risks; use `suggestion` for improvements |
| Skip `praise` entirely | Include at least one `praise` per review |
| Omit decoration on `issue` | Every `issue` must have `(blocking)` — if it's not blocking, it's a `suggestion` |
| Use `todo` for large changes | Use `suggestion` for changes requiring design decisions; `todo` is for small fixes |
| Combine unrelated concerns | One comment per concern — split multi-issue comments |

## Output Structure

1. **Summary header** — branch, commit count, files changed, build/test status, overall verdict
2. **Per-file sections** — group comments by file path, each in a fenced code block
3. **General section** — cross-cutting concerns that span multiple files
4. **How to Use** — brief instructions for copying comments into Azure DevOps
