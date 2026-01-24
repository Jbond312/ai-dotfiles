---
name: vertical-slice-architecture
description: "Vertical Slice Architecture patterns with Clean Architecture layers. Use when planning, implementing, or reviewing code in repositories that use VSA. Check .github/project-context.md to confirm the repository uses this pattern."
---

# Vertical Slice Architecture

This skill describes our approach to Vertical Slice Architecture (VSA) combined with Clean Architecture principles. Use this when the repository's `.github/project-context.md` indicates VSA is in use.

## Core Principles

**Organise by feature, not by technical layer.** Code that changes together lives together. A slice contains everything needed for a single use case—command/query, handler, validation, and endpoint.

**Maintain Clean Architecture boundaries.** While slices are self-contained, domain entities and infrastructure remain in their own layers. Slices depend inward on domain; infrastructure depends inward on domain and slices.

**Isolate slices from each other.** Slices should not directly reference other slices. If coordination is needed, use domain events, MediatR notifications, or go through the domain layer.

**Keep transport layers thin.** HTTP endpoints and message handlers should only initialise a command/query, dispatch it, and transform the result. No business logic in transport.

## Project Structure

```
src/
├── Features/                        # Vertical slices organised by feature area
│   ├── Rates/
│   │   ├── CreateRate/
│   │   │   ├── CreateRateCommand.cs
│   │   │   ├── CreateRateHandler.cs
│   │   │   ├── CreateRateValidator.cs
│   │   │   └── CreateRateEndpoint.cs
│   │   ├── AmendRate/
│   │   │   ├── AmendRateCommand.cs
│   │   │   ├── AmendRateHandler.cs
│   │   │   └── AmendRateEndpoint.cs
│   │   └── GetRate/
│   │       ├── GetRateQuery.cs
│   │       ├── GetRateHandler.cs
│   │       ├── GetRateResponse.cs
│   │       └── GetRateEndpoint.cs
│   └── Payments/
│       ├── CreatePayment/
│       └── ...
├── Domain/                          # Domain entities, value objects, domain services
│   ├── Entities/
│   ├── ValueObjects/
│   ├── Events/
│   └── Services/
└── Infrastructure/                  # External concerns, persistence, integrations
    ├── Persistence/
    │   └── RateRepository.cs
    ├── ReadStores/
    │   └── RateReadStore.cs
    ├── ExternalServices/
    └── ...
```

## Slice Components

### Command / Query

The request object that enters the slice. We use custom abstractions on top of MediatR's `IRequest`:

- `ICommand` — Write operation returning `Result`
- `ICommand<TResponse>` — Write operation returning `Result<TResponse>`
- `IQuery<TResponse>` — Read operation returning `Result<TResponse>`

```csharp
public sealed record CreateRateCommand(
    string CurrencyPair,
    decimal Rate,
    DateOnly EffectiveDate) : ICommand<Guid>;
```

```csharp
public sealed record GetRateQuery(
    string CurrencyPair,
    DateOnly AsOfDate) : IQuery<GetRateResponse>;
```

**Guidelines:**

- Use records for immutability
- Include only the data needed for this operation
- Commands use `ICommand` or `ICommand<T>`; queries use `IQuery<T>`
- All return `Result` or `Result<T>` (FluentResults)

### Handler

The MediatR handler containing the business logic for the slice. Inject `ISender` when you need to dispatch other commands/queries.

**Command handler example (write operation):**

```csharp
public sealed class CreateRateHandler : ICommandHandler<CreateRateCommand, Guid>
{
    private readonly IRateRepository _rateRepository;

    public CreateRateHandler(IRateRepository rateRepository)
    {
        _rateRepository = rateRepository;
    }

    public async Task<Result<Guid>> Handle(
        CreateRateCommand command,
        CancellationToken cancellationToken)
    {
        var rate = Rate.Create(
            command.CurrencyPair,
            command.Rate,
            command.EffectiveDate);

        await _rateRepository.AddAsync(rate, cancellationToken);

        return Result.Ok(rate.Id);
    }
}
```

**Query handler example (read operation with projection):**

```csharp
public sealed class GetRateHandler : IQueryHandler<GetRateQuery, GetRateResponse>
{
    private readonly IRateReadStore _rateReadStore;

    public GetRateHandler(IRateReadStore rateReadStore)
    {
        _rateReadStore = rateReadStore;
    }

    public async Task<Result<GetRateResponse>> Handle(
        GetRateQuery query,
        CancellationToken cancellationToken)
    {
        var rate = await _rateReadStore.GetByDateAsync(
            query.CurrencyPair,
            query.AsOfDate,
            cancellationToken);

        if (rate is null)
            return Result.Fail<GetRateResponse>("Rate not found");

        return Result.Ok(rate);
    }
}
```

**Guidelines:**

- One handler per slice—no shared handlers
- Inject `ISender` (not `IMediator`) when dispatching to other handlers
- Use domain entities and repositories for write operations
- Use read stores (adapters) for query projections
- Return `Result<T>` or `Result` using FluentResults
- Business rule validation belongs here or in domain services

### Read Stores (for Queries)

For read operations, inject a read store adapter rather than using repositories directly. This allows optimised queries and projections.

```csharp
public interface IRateReadStore
{
    Task<GetRateResponse?> GetByDateAsync(
        string currencyPair,
        DateOnly asOfDate,
        CancellationToken cancellationToken);
}
```

For very specific queries, a dedicated interface is also acceptable:

```csharp
public interface IGetRateReadStore
{
    Task<GetRateResponse?> ExecuteAsync(
        string currencyPair,
        DateOnly asOfDate,
        CancellationToken cancellationToken);
}
```

**Guidelines:**

- Read stores return DTOs/projections, not domain entities
- Implementations live in `Infrastructure/ReadStores/`
- Use stored procedures or optimised queries
- Each query slice can have its own response type—don't share projection classes

### Validator

FluentValidation validator for structural validation of the command/query.

```csharp
public sealed class CreateRateValidator : AbstractValidator<CreateRateCommand>
{
    public CreateRateValidator()
    {
        RuleFor(x => x.CurrencyPair)
            .NotEmpty()
            .Matches("^[A-Z]{6}$")
            .WithMessage("Currency pair must be 6 uppercase letters (e.g., GBPUSD)");

        RuleFor(x => x.Rate)
            .GreaterThan(0)
            .WithMessage("Rate must be positive");

        RuleFor(x => x.EffectiveDate)
            .NotEmpty()
            .WithMessage("Effective date is required");
    }
}
```

**Guidelines:**

- **Structural validation only:** Format, ranges, required fields, data types
- **Not business rules:** "Rate must not duplicate existing" belongs in the handler/domain
- Name matches the command: `{OperationName}Validator`
- Validators are optional if there's nothing structural to validate

### Response (for Queries)

The DTO returned from query slices. Co-located with the slice.

```csharp
public sealed record GetRateResponse(
    Guid RateId,
    string CurrencyPair,
    decimal Rate,
    DateOnly EffectiveDate);
```

**Guidelines:**

- Use records
- Co-locate with the slice that uses it
- **Don't share response classes across slices**—if two queries need similar data, each gets its own response type
- Handlers can return the type the API will use directly; no intermediate mapping layer required

### Endpoint

The API endpoint receives HTTP requests and dispatches to MediatR. Keep it thin.

```csharp
public static class CreateRateEndpoint
{
    public static void Map(IEndpointRouteBuilder app)
    {
        app.MapPost("/rates", Handle)
            .WithName("CreateRate")
            .WithTags("Rates")
            .Produces<Guid>(StatusCodes.Status201Created)
            .ProducesValidationProblem()
            .ProducesProblem(StatusCodes.Status400BadRequest);
    }

    private static async Task<IResult> Handle(
        CreateRateCommand command,
        ISender sender,
        CancellationToken cancellationToken)
    {
        var result = await sender.Send(command, cancellationToken);

        return result.IsSuccess
            ? Results.Created($"/rates/{result.Value}", result.Value)
            : Results.BadRequest(result.Errors);
    }
}
```

```csharp
public static class GetRateEndpoint
{
    public static void Map(IEndpointRouteBuilder app)
    {
        app.MapGet("/rates/{currencyPair}", Handle)
            .WithName("GetRate")
            .WithTags("Rates")
            .Produces<GetRateResponse>()
            .ProducesProblem(StatusCodes.Status404NotFound);
    }

    private static async Task<IResult> Handle(
        string currencyPair,
        [FromQuery] DateOnly? asOfDate,
        ISender sender,
        CancellationToken cancellationToken)
    {
        var query = new GetRateQuery(currencyPair, asOfDate ?? DateOnly.FromDateTime(DateTime.UtcNow));
        var result = await sender.Send(query, cancellationToken);

        return result.IsSuccess
            ? Results.Ok(result.Value)
            : Results.NotFound();
    }
}
```

**Guidelines:**

- Minimal API style with static class
- **Thin transport layer:** Initialise command/query, dispatch via `ISender`, transform result
- No business logic in endpoints
- Use appropriate HTTP status codes based on `Result` success/failure
- Inject `ISender`, not `IMediator`

## Validation Strategy

Validation is split between two locations:

| Validation Type    | Location                   | Examples                                                      |
| ------------------ | -------------------------- | ------------------------------------------------------------- |
| **Structural**     | FluentValidation validator | Required fields, format, ranges, data types                   |
| **Business rules** | Handler or domain          | Duplicates, permissions, state transitions, cross-field logic |

```csharp
// Structural (in validator)
RuleFor(x => x.EffectiveDate).NotEmpty();

// Business rule (in handler)
if (await _rateRepository.ExistsAsync(command.CurrencyPair, command.EffectiveDate))
    return Result.Fail("Rate already exists for this date");
```

## When to Create a New Slice

Create a new slice when:

- Adding a new use case / operation
- The operation has distinct input/output from existing slices
- The operation could be tested independently

Do NOT create a new slice when:

- Adding a minor variation to an existing operation (extend the existing slice)
- Creating shared utilities (put in appropriate layer instead)

## Cross-Slice Communication

**Avoid direct slice-to-slice dependencies.** If slice A needs something from slice B:

1. **Go through the domain** — If it's about domain logic, the domain layer should expose it
2. **Use domain events** — Slice A publishes an event, slice B subscribes
3. **Use MediatR notifications** — Similar to domain events but at application layer
4. **Query the database directly** — For read-only access, a query slice can read any data via its read store

**Never** import a handler, command, or response from another slice.

## Shared Code Guidelines

| Code Type                  | Location                          | Notes                                |
| -------------------------- | --------------------------------- | ------------------------------------ |
| Domain entities            | `src/Domain/Entities/`            | Shared across all slices             |
| Value objects              | `src/Domain/ValueObjects/`        | Shared across all slices             |
| Domain services            | `src/Domain/Services/`            | Complex domain logic                 |
| Repository interfaces      | `src/Domain/`                     | Ports for write operations           |
| Repository implementations | `src/Infrastructure/Persistence/` | Adapters using stored procedures     |
| Read store interfaces      | `src/Application/` or slice       | Ports for read operations            |
| Read store implementations | `src/Infrastructure/ReadStores/`  | Adapters with projections            |
| Cross-cutting concerns     | `src/Infrastructure/`             | HTTP policies (Polly), logging, etc. |
| Response DTOs              | In the slice folder               | Co-located, **not shared**           |

**Cross-cutting concerns** like HTTP policies (Polly), resilience patterns, and logging infrastructure should be shared—these are infrastructure concerns, not slice-specific logic.

## Co-location and Duplication

Prefer co-locating code with its slice even if it means some duplication:

**Good:** Two query slices each have their own `RateSummary` record with slightly different fields.

**Avoid:** A shared `RateSummary` in a common folder that both slices depend on, coupling them together.

**Acceptable duplication:**

- Response DTOs with similar but not identical fields
- Projection classes tailored to each query's needs
- Validators with overlapping rules

**Not acceptable duplication:**

- Domain entities (these belong in the domain layer)
- Infrastructure adapters (share these)
- Cross-cutting policies (share these)

## Testing Slices

Integration tests mirror the slice structure:

```
Tests.Integration/
└── Features/
    └── Rates/
        └── CreateRate/
            └── CreateRateTests.cs
```

Each slice should have tests covering:

- Happy path
- Validation failures (structural)
- Business rule failures
- Error conditions

```csharp
public class CreateRateTests : IntegrationTestBase
{
    [Fact]
    public async Task Should_create_rate_with_valid_request()
    {
        // Arrange
        var command = new CreateRateCommand("GBPUSD", 1.25m, DateOnly.FromDateTime(DateTime.UtcNow));

        // Act
        var result = await Sender.Send(command);

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.Value.Should().NotBeEmpty();
    }

    [Fact]
    public async Task Should_fail_with_invalid_currency_pair()
    {
        // Arrange
        var command = new CreateRateCommand("invalid", 1.25m, DateOnly.FromDateTime(DateTime.UtcNow));

        // Act
        var result = await Sender.Send(command);

        // Assert
        result.IsFailed.Should().BeTrue();
    }
}
```

## Planning a New Feature

When planning a new feature in a VSA codebase:

1. **Identify the operations** — What use cases does this feature involve? (Create, Read, Update, Delete, custom operations)
2. **Group by feature area** — What's the parent folder? (e.g., `Rates`, `Payments`)
3. **Define each slice** — One folder per operation
4. **Identify domain needs** — What entities/value objects are needed? Do they exist?
5. **Identify infrastructure needs** — Repositories for writes, read stores for queries
6. **Plan the tests** — One test class per slice, mirroring the structure

## Code Review Checklist

When reviewing code in a VSA codebase:

- [ ] Is the slice self-contained? (No imports from other slices)
- [ ] Is the slice in the correct feature area folder?
- [ ] Does the naming follow conventions? (`{Operation}Command/Query`, `{Operation}Handler`, etc.)
- [ ] Is the endpoint thin? (Initialise, dispatch, transform result only)
- [ ] Is `ISender` used (not `IMediator`)?
- [ ] Are results using `Result<T>` / `Result` (FluentResults)?
- [ ] Is structural validation in the validator?
- [ ] Are business rules in the handler or domain?
- [ ] Are domain entities used for writes?
- [ ] Are read stores used for query projections?
- [ ] Are response DTOs co-located and not shared across slices?
- [ ] Are integration tests co-located with the slice structure?
- [ ] Is there inappropriate coupling to other slices?
- [ ] Are cross-cutting concerns (Polly, etc.) properly shared?
