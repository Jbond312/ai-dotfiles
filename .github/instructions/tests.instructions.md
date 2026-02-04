---
applyTo: "**/*[Tt]ests*/**/*.cs"
description: "Testing conventions for C# test files. Applied automatically to any .cs file in a folder containing 'Tests' or 'tests'."
---

# Testing Conventions

Follow existing patterns in the test project — consistency trumps personal preference.

Refer to `dotnet-testing` skill for TDD workflow, golden examples, anti-patterns, and advanced scenarios.

## Critical Rules

- **Check CONVENTIONS.md first** — match the repo's test naming, assertions, and mocking patterns
- **Integration tests first** (honeycomb model) — a feature is not complete without passing tests
- **AAA pattern** — Arrange, Act, Assert with clear visual separation
- **One behaviour per test** — multiple asserts on the same object is fine
- **Tests must be deterministic** — no dependency on time, random, or external state
- **Test behaviour, not implementation** — tests should survive refactoring

## Test Discovery (CRITICAL)

After running `dotnet test`, check for `Total: N` where N > 0. If `Total: 0`, tests were not discovered — do not proceed.

```
dotnet test --verbosity minimal
```

**Always run from solution root.** Use `dotnet sln list` to confirm.

## Boundaries

### Never Do

- Trust a test run showing `Total: 0`
- Use `Thread.Sleep` or arbitrary delays
- Share mutable state between tests
- Test private methods directly
- Mock internal collaborators — mock at boundaries only

### Ask First

- Before adding new test utility classes or base classes
- Before changing shared test fixtures
- Before adding new external service mocks
