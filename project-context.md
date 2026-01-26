# Project Context

Repository-specific configuration. This file lives at the root of each repository.

## Repository

- **Name:** {repository-name}
- **Purpose:** {brief description}

## Architecture

- **Pattern:** Vertical Slice Architecture
- **Framework:** .NET 9, ASP.NET Core Minimal APIs

If not using VSA, remove or update this section and the `vertical-slice-architecture` skill won't apply.

## Key Directories

```
src/
├── Features/          # Vertical slices
├── Domain/            # Entities, value objects
└── Infrastructure/    # Persistence, external services

tests/
└── Integration/       # Integration tests
```

## Dependencies

- **Mediator:** MediatR with `ICommand`/`IQuery` interfaces
- **Validation:** FluentValidation
- **Results:** FluentResults
- **Testing:** xUnit, FluentAssertions, Aspire AppHost

## Conventions

- Handlers return `Result<T>` (FluentResults)
- Inject `ISender`, not `IMediator`
- Response DTOs co-located with slices (not shared)

## External Dependencies

Document stored procedures, external APIs, and third-party services that require human verification during code review:

| Name                 | Type         | Purpose            |
| -------------------- | ------------ | ------------------ |
| `sp_ProcessPayment`  | Stored Proc  | Payment processing |
| Payments Gateway API | External API | Card processing    |
