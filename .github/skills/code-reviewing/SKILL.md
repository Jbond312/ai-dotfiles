---
name: code-reviewing
description: "Code review checklist for banking applications with external dependency flagging. Use when reviewing code, checking changes before commit, or validating implementation quality. Triggers on: review, code review, check code, validate, before commit, external dependency, stored procedure, API call."
---

# Code Reviewing

## Review Checklist

### Correctness

- Does the code do what the plan specifies?
- Are edge cases handled?
- Are error conditions handled appropriately?

### Tests

- Do tests cover the stated scenarios?
- Are assertions specific (not just "no exception")?
- Do tests follow existing patterns?

### Patterns

- Does the code follow existing patterns in the repo?
- Are naming conventions followed?
- Is code in the right location?

### Banking Domain

- Is the operation idempotent?
- Are state changes auditable?
- Is input validated at boundaries?
- Are errors logged with correlation context?

### External Dependencies

- Stored procedure calls?
- External API or service calls?
- New database operations?

## Issue Categories

| Category                | Description                               | Action     |
| ----------------------- | ----------------------------------------- | ---------- |
| **Critical**            | Breaks functionality, data integrity risk | Must fix   |
| **Important**           | Maintainability, pattern violations       | Should fix |
| **Suggestion**          | Style, minor improvements                 | Can defer  |
| **External Dependency** | Requires human verification               | Flag       |

## External Dependency Flag

**Critical:** Flag any code interacting with external systems for human verification.

```
⚠️ **External Dependency Detected**

This code calls stored procedure `sp_ProcessPayment`.
Human verification required to ensure:
- Procedure exists and signature matches
- Expected behaviour is documented
- Error handling aligns with procedure's failure modes
```

## Review Report Format

```markdown
## Review Summary

**Verdict:** {Approved | Changes Requested}

### Issues Found

**Critical:** {None | List}
**Important:** {None | List}
**Suggestions:** {None | List}

### External Dependencies

{None detected | List with verification notes}

### What's Good

{Positive observations}
```

## Refactoring Suggestions

When suggesting refactoring:

1. Explain the benefit
2. Reference existing patterns: "Follow the approach in `AccountService.ValidateWithdrawal`"
3. Be specific: show target structure

Keep refactoring proportionate to the change.
