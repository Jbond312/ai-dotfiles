---
name: conventional-comments
description: "Format review feedback as conventional comments for Azure DevOps PRs. Use when producing PR review output, formatting review comments, or mapping severity to labels. Triggers on: conventional comments, PR comments, review format, comment format, label decoration."
---

# Conventional Comments

Format for structured, actionable PR review comments. Used by the PR Reviewer agent to produce copy-paste-ready feedback for Azure DevOps.

**Specification:** Based on [conventionalcomments.org](https://conventionalcomments.org/).

## Format

```
<label> [decorations]: <subject>

[discussion]
```

- **label** — categorises the comment (see Labels below)
- **decorations** — optional qualifiers in parentheses (see Decorations below)
- **subject** — main point, single line
- **discussion** — optional elaboration, evidence, or suggested fix

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

## Decorations

Decorations appear in parentheses between the label and colon. Multiple decorations are comma-separated.

### Standard Decorations

| Decoration | Meaning |
|------------|---------|
| `(blocking)` | Must be resolved before merge |
| `(non-blocking)` | Can be deferred to a follow-up |
| `(if-minor)` | Can be resolved if the change is small; otherwise defer |

### Banking Domain Decorations

| Decoration | Meaning |
|------------|---------|
| `(security)` | Security concern — injection, auth, data exposure |
| `(banking)` | Banking domain concern — idempotency, audit, financial rules |
| `(financial-integrity)` | Financial calculation or data correctness |
| `(audit)` | Audit trail or traceability concern |
| `(pii)` | Personally identifiable information exposure |
| `(performance)` | Performance concern — LINQ traps, N+1, boxing |
| `(test)` | Test quality or coverage concern |

### Combining Decorations

```
issue (blocking, security): SQL injection via string interpolation in query
```

```
suggestion (non-blocking, performance): Consider using .AsNoTracking() for read-only queries
```

## Severity Mapping

Map from `code-reviewing` skill severity levels to conventional comment labels:

| Severity (code-reviewing) | Label | Decoration | Rationale |
|---------------------------|-------|------------|-----------|
| **Critical** | `issue` | `(blocking)` | Must fix before merge |
| **Important** | `suggestion` or `todo` | varies | `todo` for specific fixes; `suggestion` for approach changes |
| **Suggestion** | `suggestion` or `nitpick` | `(non-blocking)` | `nitpick` for pure style; `suggestion` for meaningful improvements |
| **External** | `note` | `(blocking)` | Requires human verification — always blocking |

### Security Issues

Security issues from the `security-review` skill are always:

```
issue (blocking, security): <subject>
```

## Templates

### praise

```
praise: Clean separation of validation logic into the FluentValidation pipeline

The validator covers all edge cases from the requirements and the structured error response makes client integration straightforward.
```

### nitpick (non-blocking)

```
nitpick (non-blocking): Consider renaming `proc` to `processor` for clarity

Minor readability improvement — the abbreviated name requires context to understand.
```

### suggestion (non-blocking)

```
suggestion (non-blocking, performance): Replace .ToList().Count() with .Count() to avoid materialising the full collection

EF Core can translate .Count() to SQL COUNT(*) directly, avoiding loading all rows into memory.
```

### issue (blocking)

```
issue (blocking): Missing null check on payment amount allows negative transfers

If `request.Amount` is null, the implicit conversion to decimal will default to 0, allowing a zero-value transaction to be recorded without validation.

Suggested fix: Add guard clause `ArgumentNullException.ThrowIfNull(request.Amount)` or validate in the FluentValidation pipeline.
```

### issue (blocking, security)

```
issue (blocking, security): Account number logged in plain text at line 47

PII must not appear in log output. Use the internal CustomerId instead.

See: security-review checklist — Sensitive Data Exposure
```

### todo

```
todo: Add unit test for the rejection path when balance is insufficient

The happy path is covered but the insufficient-funds scenario is untested.
```

### question

```
question: Is this timeout value (30s) intentional or a placeholder?

The default HttpClient timeout is 100s. If 30s is a business requirement, consider extracting to configuration.
```

### thought

```
thought: This could benefit from the Result pattern used elsewhere in the codebase

Not a change for this PR, but the exception-based error handling here diverges from the Result<T> pattern in other handlers.
```

### chore

```
chore (non-blocking): Remove unused `using System.Linq` directive

The LINQ namespace is imported but no LINQ methods are used in this file.
```

### note (blocking)

```
note (blocking): This handler calls stored procedure sp_ProcessRefund which needs to exist in the database

Verify the stored procedure exists and its signature matches the parameters passed here. This cannot be validated from code alone.
```

### note (blocking, banking)

```
note (blocking, banking): This operation modifies account balance without an idempotency key

If the request is retried (network failure, timeout), duplicate debits could occur. Verify this is handled upstream or add an idempotency key to the command.
```

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Mark style issues as `(blocking)` | Use `nitpick (non-blocking)` for style |
| Write a label with no discussion | Always include at least one sentence of discussion explaining *why* |
| Use `issue` for suggestions | Reserve `issue` for actual bugs or risks; use `suggestion` for improvements |
| Skip `praise` entirely | Include at least one `praise` per review — acknowledge good work |
| Omit decoration on `issue` | Every `issue` must have `(blocking)` — if it's not blocking, it's a `suggestion` |
| Use `todo` for large changes | Use `suggestion` for changes requiring design decisions; `todo` is for small, obvious fixes |
| Combine unrelated concerns | One comment per concern — split multi-issue comments into separate entries |

## Output Structure

When producing a full PR review, organise comments as:

1. **Summary header** — branch, commit count, files changed, build/test status, overall verdict
2. **Per-file sections** — group comments by file path, each in a fenced code block
3. **General section** — cross-cutting concerns that span multiple files
4. **How to Use** — brief instructions for copying comments into Azure DevOps
