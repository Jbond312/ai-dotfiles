---
name: architecture-patterns
description: "Architecture pattern reference for .NET applications. Use when evaluating, choosing, or reviewing architectural patterns — Vertical Slice, Clean Architecture, CQRS, N-Tier. Triggers on: architecture, vertical slice, clean architecture, CQRS, layers, domain, bounded context, dependency direction, project structure."
---

# Architecture Patterns Reference

**This skill is not prescriptive.** The Repo Analyser discovers which pattern a repository uses, and CONVENTIONS.md documents it. This skill provides reference material for understanding, evaluating, and correctly implementing the pattern that has been chosen.

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's established architecture. Verify code follows that pattern — do not suggest switching patterns mid-project.

## Pattern: Vertical Slice Architecture

Organise code by feature, not by technical layer. Each feature is a self-contained "slice" through the stack.

### Folder Structure

```
src/
├── Features/
│   ├── Payments/
│   │   ├── CreatePayment.cs          # Command + Handler + Validator
│   │   ├── GetPayment.cs             # Query + Handler
│   │   ├── ListPayments.cs           # Query + Handler
│   │   └── PaymentModels.cs          # Request/Response DTOs
│   ├── Accounts/
│   │   ├── OpenAccount.cs
│   │   ├── GetAccountBalance.cs
│   │   └── AccountModels.cs
│   └── Transfers/
│       ├── InitiateTransfer.cs
│       └── TransferModels.cs
├── Common/
│   ├── Behaviours/                    # Cross-cutting MediatR behaviours
│   └── Models/                        # Shared value objects
└── Program.cs
```

### Dependency Direction

Features depend inward on `Common/`. Features do NOT depend on each other. Cross-feature communication goes through shared abstractions (events, mediator) not direct references.

### When to Use

- Team wants fast feature delivery with minimal cross-cutting changes
- Features are relatively independent
- Medium to large codebases where navigation by feature is easier than by layer
- Using MediatR or similar handler-per-request pattern

### Trade-offs

| Pro | Con |
|-----|-----|
| Easy to find all code for a feature | Cross-cutting concerns need explicit sharing strategy |
| Features can evolve independently | Risk of code duplication if common patterns aren't extracted |
| New team members find relevant code quickly | Less obvious where shared infrastructure lives |
| Deleting a feature is straightforward | Requires discipline to avoid feature-to-feature coupling |

## Pattern: Clean Architecture

Organise code in concentric layers. Inner layers define abstractions; outer layers implement them. Dependencies point inward only.

### Layers

```
┌─────────────────────────────────────┐
│         Presentation / API          │  ← Controllers, Minimal APIs
├─────────────────────────────────────┤
│          Infrastructure             │  ← EF Core, Dapper, Service Bus, external APIs
├─────────────────────────────────────┤
│           Application               │  ← Use cases, handlers, DTOs, interfaces
├─────────────────────────────────────┤
│             Domain                  │  ← Entities, value objects, domain services
└─────────────────────────────────────┘
```

### Folder Structure

```
src/
├── Domain/
│   ├── Entities/
│   │   ├── Account.cs
│   │   └── Payment.cs
│   ├── ValueObjects/
│   │   ├── Money.cs
│   │   └── AccountNumber.cs
│   ├── Exceptions/
│   │   └── InsufficientFundsException.cs
│   └── Interfaces/
│       └── IAccountRepository.cs
├── Application/
│   ├── Payments/
│   │   ├── Commands/
│   │   │   ├── CreatePaymentCommand.cs
│   │   │   └── CreatePaymentHandler.cs
│   │   └── Queries/
│   │       ├── GetPaymentQuery.cs
│   │       └── GetPaymentHandler.cs
│   ├── Common/
│   │   ├── Interfaces/
│   │   │   └── IUnitOfWork.cs
│   │   └── Behaviours/
│   │       └── ValidationBehaviour.cs
│   └── DependencyInjection.cs
├── Infrastructure/
│   ├── Persistence/
│   │   ├── AccountRepository.cs
│   │   └── DapperContext.cs
│   ├── Messaging/
│   │   └── PaymentEventPublisher.cs
│   └── DependencyInjection.cs
└── Api/
    ├── Controllers/
    │   └── PaymentsController.cs
    └── Program.cs
```

### Dependency Direction

```
Api → Application → Domain
Infrastructure → Application → Domain

Domain depends on NOTHING
Application defines interfaces, Infrastructure implements them
Api and Infrastructure are at the same level (both depend on Application)
```

### When to Use

- Complex domain logic that benefits from isolation
- Multiple entry points (API, background workers, CLI) sharing the same application logic
- Teams experienced with dependency inversion and interface-driven design
- Long-lived projects where testability and maintainability are priorities

### Trade-offs

| Pro | Con |
|-----|-----|
| Domain logic is isolated and testable | More boilerplate (interfaces, mapping between layers) |
| Clear dependency rules prevent coupling | Can feel heavy for simple CRUD |
| Infrastructure swappable (EF → Dapper) | New developers need to understand the dependency rule |
| Enforces separation of concerns | Risk of "architecture astronaut" over-abstraction |

## Pattern: CQRS (without Event Sourcing)

Separate the read path (Queries) from the write path (Commands). Each has its own model optimised for its purpose. This is NOT event sourcing — state is stored directly, not derived from events.

### Structure

```csharp
// Command — changes state
public record CreatePaymentCommand(
    long SourceAccountId,
    long DestinationAccountId,
    decimal Amount,
    string Currency,
    Guid IdempotencyKey) : IRequest<ErrorOr<PaymentResult>>;

public class CreatePaymentHandler : IRequestHandler<CreatePaymentCommand, ErrorOr<PaymentResult>>
{
    // Uses write model (domain entity, repository with full aggregate)
    public async Task<ErrorOr<PaymentResult>> Handle(
        CreatePaymentCommand request, CancellationToken ct)
    {
        // Validation, domain logic, persistence
    }
}

// Query — reads state (can use a different, optimised model)
public record GetPaymentQuery(long PaymentId) : IRequest<ErrorOr<PaymentDto>>;

public class GetPaymentHandler : IRequestHandler<GetPaymentQuery, ErrorOr<PaymentDto>>
{
    // Can read directly from DB with Dapper (no domain model needed)
    public async Task<ErrorOr<PaymentDto>> Handle(
        GetPaymentQuery request, CancellationToken ct)
    {
        return await _connection.QuerySingleOrDefaultAsync<PaymentDto>(
            "SELECT PaymentId, Amount, Status FROM Banking.Payment WHERE PaymentId = @Id",
            new { Id = request.PaymentId });
    }
}
```

### Combining with Other Patterns

CQRS combines naturally with Clean Architecture, Vertical Slice, or both:

- **CQRS + Clean Architecture:** Commands/Queries in Application layer, handlers use Domain entities for writes, Dapper for reads
- **CQRS + Vertical Slice:** Each feature folder has its own Commands and Queries
- **CQRS + Clean Architecture + Vertical Slice:** Clean Architecture's dependency direction with features organised as slices within the Application layer, each slice containing its own Commands and Queries

### When to Use

- Read and write models differ significantly (complex writes, simple reads)
- Read-heavy systems that benefit from optimised query models
- Teams that want to use different data access for reads vs writes (Dapper for reads, EF Core for writes)

### Trade-offs

| Pro | Con |
|-----|-----|
| Reads and writes optimised independently | Two models to maintain |
| Queries can bypass domain model for performance | Consistency between read/write models |
| Naturally separates business logic from reporting | Overkill for simple CRUD with identical read/write shapes |

## Pattern: N-Tier / Layered

Traditional layered architecture with top-down dependencies. Simple and widely understood.

### Folder Structure

```
src/
├── Controllers/
│   └── PaymentsController.cs
├── Services/
│   ├── IPaymentService.cs
│   └── PaymentService.cs
├── Repositories/
│   ├── IPaymentRepository.cs
│   └── PaymentRepository.cs
├── Models/
│   ├── Payment.cs
│   └── PaymentDto.cs
└── Program.cs
```

### Dependency Direction

```
Controllers → Services → Repositories → Database
```

Each layer only calls the layer directly below it.

### When to Use

- Small to medium applications with straightforward business logic
- Teams new to .NET or wanting minimal architectural overhead
- Prototypes and MVPs where speed matters more than long-term structure
- CRUD-heavy applications without complex domain logic

### Trade-offs

| Pro | Con |
|-----|-----|
| Simple, widely understood | Service classes tend to grow into "god objects" |
| Low ceremony, fast to start | Hard to test business logic in isolation |
| Clear top-down flow | Infrastructure concerns leak into business logic |
| Most tutorials and examples use this | Doesn't scale well for complex domains |

## Combining Patterns

### CQRS + Clean Architecture

```
Domain/          → Entities, value objects (shared by commands)
Application/
├── Commands/    → Write operations using domain model
├── Queries/     → Read operations using lightweight DTOs
└── Common/      → Shared interfaces, behaviours
Infrastructure/  → Repository implementations (EF for writes, Dapper for reads)
Api/             → Controllers dispatching Commands and Queries
```

### CQRS + Vertical Slice

```
Features/
├── Payments/
│   ├── CreatePayment.cs      → Command + Handler (write model)
│   ├── GetPayment.cs         → Query + Handler (read model, Dapper)
│   └── ListPayments.cs       → Query + Handler (read model, Dapper)
```

### CQRS + Clean Architecture + Vertical Slice

All three work together: Clean Architecture provides the dependency direction and layer separation, Vertical Slice organises features within the Application layer, and CQRS separates the read/write models within each slice.

```
Domain/                    → Entities, value objects, domain services
Application/
├── Features/
│   ├── Payments/
│   │   ├── Commands/
│   │   │   ├── CreatePaymentCommand.cs
│   │   │   └── CreatePaymentHandler.cs    → Uses domain model, EF/repository for writes
│   │   └── Queries/
│   │       ├── GetPaymentQuery.cs
│   │       └── GetPaymentHandler.cs       → Uses Dapper, flat DTOs for reads
│   └── Transfers/
│       ├── Commands/
│       │   └── ...
│       └── Queries/
│           └── ...
└── Common/                → Shared interfaces, behaviours
Infrastructure/            → Repository and query implementations
Api/                       → Controllers dispatching Commands and Queries
```

## Decision Guide

| Factor | Vertical Slice | Clean Architecture | CQRS | N-Tier |
|--------|---------------|-------------------|------|--------|
| **Team size** | Any | Medium-Large | Medium-Large | Small-Medium |
| **Domain complexity** | Medium | High | High (read/write asymmetry) | Low-Medium |
| **Read/write asymmetry** | N/A | N/A | High (main driver) | Low |
| **Time to first feature** | Fast | Moderate | Moderate | Fastest |
| **Long-term maintainability** | Good | Excellent | Good-Excellent | Fair |
| **Testability** | Good | Excellent | Good | Fair |
| **Learning curve** | Low-Medium | Medium-High | Medium | Low |
| **Boilerplate** | Low | High | Medium | Low |

## Anti-Patterns

### Circular Dependencies

```csharp
// BAD: Service A depends on Service B which depends on Service A
public class PaymentService
{
    private readonly AccountService _accountService; // AccountService also depends on PaymentService!
}

// GOOD: Extract shared logic into a third service, or use events/mediator
public class PaymentService
{
    private readonly IMediator _mediator; // Decouple via mediator
}
```

### God Service

```csharp
// BAD: One service does everything
public class AccountService
{
    public Task CreateAccount() { }
    public Task GetBalance() { }
    public Task Transfer() { }
    public Task CalculateInterest() { }
    public Task GenerateStatement() { }
    public Task CloseAccount() { }
    public Task FreezeAccount() { }
    // ... 50 more methods
}

// GOOD: Separate by responsibility (handlers, services per bounded context)
```

### Wrong-Layer Placement

```csharp
// BAD: SQL queries in a controller
[HttpGet("{id}")]
public async Task<IActionResult> Get(long id)
{
    using var conn = new SqlConnection(_connectionString);
    var account = await conn.QuerySingleAsync<Account>(
        "SELECT * FROM Account WHERE Id = @Id", new { Id = id });
    return Ok(account);
}

// GOOD: Data access in the appropriate layer (repository, handler)
[HttpGet("{id}")]
public async Task<IActionResult> Get(long id, CancellationToken ct)
{
    var result = await _handler.GetAccount(id, ct);
    return result.Match(Ok, errors => Problem(errors));
}
```

### Inconsistent Mixing

```csharp
// BAD: Some features use Clean Architecture, others use N-Tier in the same project
src/
├── Domain/Accounts/          ← Clean Architecture
├── Services/PaymentService.cs ← N-Tier
├── Features/Transfers/       ← Vertical Slice

// GOOD: Pick one pattern and follow it consistently
```

## Resilience & Auditability

1. **Domain layer encapsulates critical business rules** — Balance calculations, transfer validation, interest computation, and regulatory checks belong in the domain layer (Clean Architecture) or within the feature handler (Vertical Slice). Never scatter business rules across controllers, services, and repositories
2. **Audit trail favours explicit command/event patterns** — CQRS or handler-per-request patterns naturally produce an audit trail (every mutation is an explicit command). N-Tier services with many methods make auditing harder to enforce consistently
3. **CQRS benefits for reporting** — Separate read models can be optimised for regulatory or compliance report generation without affecting write performance. Read-side projections can serve reporting queries without loading full domain aggregates
4. **Consistency boundaries** — Operations that must be atomic (debit + credit) must live within a single bounded context. Cross-context operations that require atomicity need saga or choreography patterns

## Review Checklist

### Pattern Compliance

- [ ] Code follows the architecture documented in CONVENTIONS.md?
- [ ] New features placed in the correct location per the established pattern?
- [ ] Dependencies point in the correct direction (no outward dependencies from inner layers)?
- [ ] No circular dependencies between components?

### Separation of Concerns

- [ ] Business logic in the appropriate layer (domain/handler, not controller)?
- [ ] Data access in the appropriate layer (infrastructure/repository, not controller)?
- [ ] No "god services" with too many responsibilities?
- [ ] Cross-cutting concerns handled via middleware or behaviours, not duplicated?

### Consistency

- [ ] Same pattern applied across all features in the project?
- [ ] No mixing of architectural patterns within the same bounded context?
- [ ] Naming conventions consistent with the established pattern?

### Resilience & Auditability

- [ ] Critical business rules encapsulated in domain/handler layer?
- [ ] Mutation operations traceable for audit?
- [ ] Consistency boundaries respected for atomic operations?
- [ ] Read models separated from write models where beneficial?
