# Project Context

This document describes the architectural patterns, conventions, and context specific to this repository. Copilot agents read this file to understand how to structure code appropriately.

## Azure DevOps

- **Organization:** {Your Azure DevOps organization name, e.g., "contoso"}
- **Project:** {Your Azure DevOps project name, e.g., "payments-platform"}

## Team

- **Team name:** {Your Azure DevOps team name, e.g., "Platform Team"}
- **Team ID:** {Team GUID from Azure DevOps - find via Project Settings > Teams > select team > URL contains the ID}

The team name is used by scripts to construct:

- **Area Path filter:** `{Project}\{Team}` — scopes work items to your team
- **Iteration lookup:** Gets the team's current sprint

For example, if your project is "PaymentsPlatform" and team is "Platform Team":

- Area Path: `PaymentsPlatform\Platform Team`

**Finding your team name:** In Azure DevOps, go to Project Settings > Teams. The team name is displayed in the list. This must match exactly (case-sensitive) for queries to return the correct work items.

## Current User

- **Display name:** {Your name as it appears in Azure DevOps, e.g., "Jane Smith"}
- **Email:** {Your Azure DevOps email, e.g., "jane.smith@company.com"}
- **User ID:** {Your Azure DevOps user GUID - optional, for filtering PRs}

This is used when agents need to identify you (e.g., filtering out your own PRs, checking your in-progress work). The Microsoft Azure DevOps MCP doesn't reliably provide current user info, so we configure it here.

**Finding your user ID:** In Azure DevOps, go to your profile settings. The URL contains your user ID, or use the "Connection Data" REST API.

## Work Item Types

- **Backlog item type:** Product Backlog Item
- **Research/exploration type:** Spike

If your project uses different work item types (e.g., "User Story" instead of "Product Backlog Item"), update the types above and agents will adjust their queries accordingly.

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
