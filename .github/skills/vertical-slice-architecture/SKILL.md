---
name: vertical-slice-architecture
description: "Vertical Slice Architecture patterns with Clean Architecture layers. Use when planning features, creating slices, implementing handlers, or reviewing VSA code structure. Triggers on: VSA, vertical slice, feature slice, handler, command, query, MediatR, slice structure."
---

# Vertical Slice Architecture

## Core Principles

**Organise by feature, not layer.** Code that changes together lives together. A slice contains everything for a single use case.

**Maintain Clean Architecture boundaries.** Domain and infrastructure remain in their own layers. Slices depend inward on domain.

**Isolate slices from each other.** No direct slice-to-slice references. Use domain events or go through domain layer.

**Keep transport layers thin.** Endpoints initialise command/query, dispatch, transform result. No business logic.

## Project Structure

```
src/
├── Features/                        # Vertical slices by feature area
│   ├── Rates/
│   │   ├── CreateRate/
│   │   │   ├── CreateRateCommand.cs
│   │   │   ├── CreateRateHandler.cs
│   │   │   ├── CreateRateValidator.cs
│   │   │   └── CreateRateEndpoint.cs
│   │   └── GetRate/
│   │       ├── GetRateQuery.cs
│   │       ├── GetRateHandler.cs
│   │       ├── GetRateResponse.cs
│   │       └── GetRateEndpoint.cs
├── Domain/                          # Entities, value objects, domain services
└── Infrastructure/                  # Persistence, external services
```

## Quick Reference

| Component     | Purpose               | Location                       |
| ------------- | --------------------- | ------------------------------ |
| Command/Query | Request object        | `Features/{Area}/{Operation}/` |
| Handler       | Business logic        | Same slice folder              |
| Validator     | Structural validation | Same slice folder              |
| Response      | Query DTO             | Same slice folder (not shared) |
| Endpoint      | HTTP thin layer       | Same slice folder              |
| Read Store    | Query projections     | `Infrastructure/ReadStores/`   |

## Key Conventions

- Commands: `ICommand` or `ICommand<T>`; queries: `IQuery<T>`
- All handlers return `Result<T>` (FluentResults)
- Inject `ISender`, not `IMediator`
- Response DTOs co-located and **not shared** across slices
- Validators: structural only; business rules in handlers

## Detailed References

**Slice Components:** See [reference/slice-components.md](reference/slice-components.md) for full code examples.

**Code Review Checklist:** See [reference/code-review-checklist.md](reference/code-review-checklist.md) for VSA-specific review criteria.

## When to Create a New Slice

**Create** when adding a new use case with distinct input/output.

**Don't create** when adding minor variation (extend existing) or shared utilities (use appropriate layer).

## Cross-Slice Communication

Never import handlers, commands, or responses from other slices. Instead: domain layer, domain events, MediatR notifications, or direct database query (read-only).
