# Project Context

This document describes the architectural patterns, conventions, and context specific to this repository. Copilot agents read this file to understand how to structure code appropriately.

## Azure DevOps

- **Organization:** {Your Azure DevOps organization name, e.g., "contoso"}
- **Project:** {Your Azure DevOps project name, e.g., "payments-platform"}

## Team

- **Team name:** {Your Azure DevOps team name, e.g., "Platform Team"}
- **Team ID:** {Team GUID from Azure DevOps - find via Project Settings > Teams > select team > URL contains the ID}

The team name is used to construct:

- **Area Path filter:** `{Project}\{Team}` — scopes work items to your team
- **Iteration Path filter:** `@CurrentIteration('[{Project}]\{Team}')` — scopes to current sprint

For example, if your project is "PaymentsPlatform" and team is "Platform Team":

- Area Path: `PaymentsPlatform\Platform Team`
- Iteration: `@CurrentIteration('[PaymentsPlatform]\Platform Team')`

**Finding your team name:** In Azure DevOps, go to Project Settings > Teams. The team name is displayed in the list. This must match exactly (case-sensitive) for WIQL queries to work.

## Work Item Types

- **Backlog item type:** Product Backlog Item
- **Bug tracking:** Bugs are treated as backlog items

If your project uses different work item types (e.g., "User Story" instead of "Product Backlog Item"), update the type above and agents will adjust their queries accordingly.

## Architecture

- **Pattern:** Vertical Slice Architecture with Clean Architecture layers
- **Feature location:** `src/Features/{FeatureArea}/{OperationName}/`
- **Domain location:** `src/Domain/`
- **Infrastructure location:** `src/Infrastructure/`

## Slice Structure

Each slice follows this structure:

```
src/Features/{FeatureArea}/{OperationName}/
├── {OperationName}Command.cs       # or Query.cs for read operations
├── {OperationName}Handler.cs       # MediatR handler
├── {OperationName}Validator.cs     # FluentValidation validator (structural validation)
├── {OperationName}Response.cs      # Response DTO (for queries, co-located)
└── {OperationName}Endpoint.cs      # API endpoint (thin transport layer)
```

## Key Patterns

- **Mediator:** MediatR with custom `ICommand<T>`, `ICommand`, `IQuery<T>` abstractions
- **Results:** FluentResults (`Result<T>`, `Result`)
- **Validation:** FluentValidation for structural; business rules in handler/domain
- **Persistence:** Stored procedures via repositories (writes) and read stores (queries)
- **API Style:** Minimal APIs with thin endpoint classes
- **Dispatch:** Use `ISender` (not `IMediator`)

## Testing

- **Integration test project:** `Tests.Integration`
- **Test structure mirrors slices:** `Tests.Integration/Features/{FeatureArea}/{OperationName}/`
- **Uses Aspire:** Yes
- **External service mocking:** WireMock

## Domain

- **Primary domain:** {describe the domain, e.g., "Payment processing", "Interest calculation"}
- **Key aggregates:** {list main aggregates, e.g., "Payment, Account, Transaction"}

## External Dependencies

{List external services and how they're handled in tests}

| Service       | Purpose        | Test Approach |
| ------------- | -------------- | ------------- |
| {ServiceName} | {What it does} | WireMock      |

## Cross-Cutting Concerns

These are shared across slices (not co-located):

- HTTP resilience policies (Polly)
- Logging infrastructure
- Authentication/authorisation

## Notes

{Any other context that would help agents understand this codebase}
