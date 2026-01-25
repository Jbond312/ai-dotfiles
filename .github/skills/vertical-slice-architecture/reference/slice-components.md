# VSA Slice Components

Detailed examples of each component in a vertical slice.

## Command / Query

```csharp
// Command (write operation)
public sealed record CreateRateCommand(
    string CurrencyPair,
    decimal Rate,
    DateOnly EffectiveDate) : ICommand<Guid>;

// Query (read operation)
public sealed record GetRateQuery(
    string CurrencyPair,
    DateOnly AsOfDate) : IQuery<GetRateResponse>;
```

## Handler

**Command handler:**

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

**Query handler:**

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

## Validator

FluentValidation for **structural** validation only:

```csharp
public sealed class CreateRateValidator : AbstractValidator<CreateRateCommand>
{
    public CreateRateValidator()
    {
        RuleFor(x => x.CurrencyPair)
            .NotEmpty()
            .Matches("^[A-Z]{6}$")
            .WithMessage("Currency pair must be 6 uppercase letters");

        RuleFor(x => x.Rate)
            .GreaterThan(0);

        RuleFor(x => x.EffectiveDate)
            .NotEmpty();
    }
}
```

**Validation split:** Structural (format, required, ranges) in validator. Business rules in handler/domain.

## Endpoint

Minimal API, thin layer:

```csharp
public static class CreateRateEndpoint
{
    public static void Map(IEndpointRouteBuilder app)
    {
        app.MapPost("/rates", Handle)
            .WithName("CreateRate")
            .WithTags("Rates")
            .Produces<Guid>(StatusCodes.Status201Created)
            .ProducesValidationProblem();
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

## Read Store

For queries, inject a read store returning DTOs:

```csharp
public interface IRateReadStore
{
    Task<GetRateResponse?> GetByDateAsync(
        string currencyPair,
        DateOnly asOfDate,
        CancellationToken cancellationToken);
}
```

Implementations in `Infrastructure/ReadStores/`.

## Response

Query DTO, co-located with slice:

```csharp
public sealed record GetRateResponse(
    Guid RateId,
    string CurrencyPair,
    decimal Rate,
    DateOnly EffectiveDate);
```

**Don't share across slices.** Prefer co-location even with some duplication.

## Testing

Mirror slice structure:

```csharp
public class CreateRateTests : IntegrationTestBase
{
    [Fact]
    public async Task Should_create_rate_with_valid_request()
    {
        var command = new CreateRateCommand("GBPUSD", 1.25m, DateOnly.FromDateTime(DateTime.UtcNow));
        var result = await Sender.Send(command);

        result.IsSuccess.Should().BeTrue();
        result.Value.Should().NotBeEmpty();
    }
}
```
