---
name: git-committing
description: "Conventional commit message format with type, scope, and description. Use when committing code, writing commit messages, or preparing changes for commit. Triggers on: commit, git commit, commit message, conventional commit, feat, fix, refactor."
---

# Git Committing

Commit messages follow Conventional Commits format.

## Format

```
<type>(<scope>): <description>

[optional body]
```

## Types

| Type       | Use When                                  |
| ---------- | ----------------------------------------- |
| `feat`     | Adding new functionality                  |
| `fix`      | Correcting a bug                          |
| `test`     | Adding or updating tests (primary change) |
| `refactor` | Restructuring without behaviour change    |
| `docs`     | Documentation only                        |
| `chore`    | Maintenance, dependencies                 |

## Scope

Derive from:

- Repository hint in work item title: `[payments]` → scope `payments`
- Primary domain area affected
- Component or module name

Check recent commits for consistency: `git log --oneline -20`

## Description Rules

- Imperative mood: "add" not "added" or "adds"
- Lowercase throughout
- No trailing period
- Under 50 characters (hard limit: 72)
- Specific: "add balance validation to payment processor" not "update code"

## Body (Optional)

Include when the "what" isn't obvious, important "why" context exists, or the change has notable implications. Separate from subject with blank line. Wrap at 72 characters.

## Examples

**Feature:**

```
feat(payments): add balance validation to payment processor

Validates account balance before processing payment requests.
Returns DeclinedResult with InsufficientFunds reason when
balance is below the requested amount.
```

**Fix:**

```
fix(accounts): prevent negative balance on concurrent withdrawals
```

**Test:**

```
test(payments): add integration tests for refund flow
```

**Refactor:**

```
refactor(api): extract validation into dedicated middleware
```

## Commands

```bash
git commit -m "feat(payments): add balance validation"
git log -1 --oneline  # verify
```
