# Project Context

This file provides repository-specific context for AI agents.

## Repository

- **Name:** {repository-name}
- **Purpose:** {brief description}

## Architecture

- **Pattern:** Vertical Slice Architecture (see `vertical-slice-architecture` skill)
- **Framework:** .NET 9, ASP.NET Core Minimal APIs
- **Messaging:** Azure Service Bus
- **Database:** Azure SQL Database
- **Hosting:** Azure Kubernetes Service (AKS)

## Azure DevOps

- **Organization:** {your-org}
- **Project:** {your-project}

## Team

- **Team name:** {Your Team Name}
- **Team ID:** {team-guid-for-pr-queries}
- **Area Path:** {Project}\\{Team}

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

- **Mediator:** MediatR with custom `ICommand`/`IQuery` interfaces
- **Validation:** FluentValidation
- **Results:** FluentResults
- **Testing:** xUnit, FluentAssertions, Aspire AppHost

## Conventions

- Handlers return `Result<T>` (FluentResults)
- Inject `ISender`, not `IMediator`
- Read stores for query projections
- Response DTOs co-located with slices (not shared)

## External Dependencies

Document stored procedures, external APIs, and third-party services here:

| Name                | Type         | Purpose            |
| ------------------- | ------------ | ------------------ |
| `sp_ProcessPayment` | Stored Proc  | Payment processing |
| Payments Gateway    | External API | Card processing    |
