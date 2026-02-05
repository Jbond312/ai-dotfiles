---
name: csharp-coding
description: "C# coding standards, patterns, and best practices for .NET development. Use when writing C# code, implementing features, creating classes, or reviewing code quality."
---

# C# Coding Standards

## When to Use This Skill

Use this skill when you need to:

- Write new C# classes, methods, or handlers
- Implement features in a .NET codebase
- Review C# code for quality and consistency
- Understand C# best practices for banking applications

## Prerequisites

**Before writing code:** Read `.planning/CONVENTIONS.md` for repository-specific patterns. If it doesn't exist, the calling agent should invoke the `Repo Analyser` subagent first.

## Hard Rules

### Must

1. **Follow repository conventions** — Check `.planning/CONVENTIONS.md` for this repo's specific patterns
2. **Use the existing test framework** — Don't introduce new test libraries
3. **Match existing code style** — Namespaces, formatting, naming should be consistent
4. **Handle nulls explicitly** — Use nullable reference types, null checks, or Option/Maybe patterns
5. **Make dependencies explicit** — Inject via constructor, never use service locator
6. **Validate inputs at boundaries** — Public methods and API endpoints must validate

### Must Not

1. **DateTime.Now / DateTime.UtcNow** — Use injected `IDateTimeProvider` or `TimeProvider` for testability
2. **Catch generic Exception without re-throwing** — Catch specific exceptions or re-throw after logging
3. **Magic strings for configuration** — Use strongly-typed options pattern
4. **Public fields** — Use properties, even for simple DTOs
5. **Static state** — Avoid static mutable state; use DI scopes instead
6. **Hardcoded connection strings or secrets** — Use configuration/secrets management

## Banking-Specific Rules

### Financial Calculations

- Use `decimal` for money, never `double` or `float`
- Be explicit about rounding: `Math.Round(amount, 2, MidpointRounding.ToEven)`
- Document rounding rules in comments when they're domain-specific

### Idempotency

- Operations that can be retried must be idempotent
- Use idempotency keys for external API calls
- Check for existing records before insert in upsert scenarios

### Audit Trail

- State changes on sensitive entities should be logged
- Include correlation IDs in all log entries
- Never log sensitive data (account numbers, PII) in plain text
