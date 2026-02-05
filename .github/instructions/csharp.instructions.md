---
applyTo: "**/*.cs"
description: "C# coding conventions for all C# files"
---

# C# Conventions

**Check `.planning/CONVENTIONS.md` first** for repo-specific patterns. These instructions are general; conventions are authoritative.

Modern idiomatic C#: file-scoped namespaces, primary constructors, collection expressions.

Use `var` when type is obvious; explicit types when it aids readability.

## Immutability

Favour immutability: `readonly` fields, `init` properties, records for DTOs. Avoid mutable static state.

## Naming

Name precisely: methods are verbs (`ProcessPayment`), booleans read as questions (`IsValid`, `HasExpired`).

## Error Handling

Exceptions for exceptional conditions only. Return `Result<T>` for expected failures (validation, business rules). Catch specific types, preserve inner exceptions, include context.

## Async/Await

Use consistently throughout call stack. Never block with `.Result` or `.Wait()`. Use `ConfigureAwait(false)` in library code. Prefer `ValueTask<T>` for hot paths.
