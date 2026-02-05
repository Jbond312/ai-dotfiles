---
name: api-design
description: "ASP.NET API design standards for .NET applications. Use when writing, reviewing, or designing API endpoints — controllers, minimal APIs, HTTP status codes, versioning, pagination, ProblemDetails. Triggers on: API, endpoint, controller, minimal API, route, HTTP, REST, ProblemDetails, versioning, pagination."
---

# API Design Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's API style (Controllers vs Minimal APIs). Follow the established style consistently.

## Hard Rules for Review

### Must Flag as Critical

1. **No ProblemDetails for errors** — Error responses that return plain strings or custom objects instead of RFC 9457 ProblemDetails
2. **Wrong HTTP status codes** — Returning 200 with an error body, 404 for validation failures, or 500 for business rule violations
3. **Missing CancellationToken** — Async endpoints without `CancellationToken` parameter
4. **SQL injection via query parameters** — String interpolation or concatenation in queries built from request values
5. **Unbounded collections** — Endpoints returning full table contents without pagination

### Must Flag as Important

1. **Verbs in resource paths** — `/api/createPayment` instead of `POST /api/payments`
2. **Missing versioning** — Breaking changes without API version increment
3. **No request validation** — Endpoints that trust client input without validation at the boundary
4. **Inconsistent naming** — Mixed plural/singular resource names, inconsistent casing

## HTTP Status Code Reference

| Status | Meaning | Example |
|--------|---------|-----------------|
| 200 OK | Successful retrieval or update | Get account balance |
| 201 Created | Resource created | New payment initiated |
| 202 Accepted | Async processing started | Transfer queued for batch |
| 204 No Content | Successful action, no body | Account preferences updated |
| 400 Bad Request | Malformed request / validation failure | Invalid sort code format |
| 401 Unauthorized | Missing or invalid authentication | Expired JWT |
| 403 Forbidden | Authenticated but not authorised | Access to another customer's account |
| 404 Not Found | Resource doesn't exist | Account ID not in system |
| 409 Conflict | Business rule violation | Insufficient funds, account frozen |
| 422 Unprocessable Entity | Valid syntax but invalid semantics | Transfer to self, negative amount |
| 429 Too Many Requests | Rate limit exceeded | Too many payment requests |
| 500 Internal Server Error | Unhandled server error | Database connection failure |

## Controller Pattern

```csharp
[ApiController]
[Route("api/v{version:apiVersion}/[controller]")]
[ApiVersion("1.0")]
[Produces("application/json")]
public class PaymentsController : ControllerBase
{
    private readonly IPaymentHandler _handler;

    public PaymentsController(IPaymentHandler handler) => _handler = handler;

    /// <summary>Creates a new payment.</summary>
    /// <response code="201">Payment created</response>
    /// <response code="409">Business rule violation (insufficient funds, frozen account)</response>
    [HttpPost]
    [ProducesResponseType<PaymentResponse>(StatusCodes.Status201Created)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Create(
        [FromBody] CreatePaymentRequest request,
        [FromHeader(Name = "Idempotency-Key")] string idempotencyKey,
        CancellationToken cancellationToken)
    {
        var result = await _handler.CreatePayment(
            request.ToCommand(idempotencyKey), cancellationToken);

        return result.Match(
            payment => CreatedAtAction(nameof(Get), new { id = payment.Id }, payment),
            errors => Problem(errors) // Map to ProblemDetails — see error-handling skill
        );
    }

    [HttpGet("{id:long}")]
    [ProducesResponseType<PaymentResponse>(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Get(long id, CancellationToken cancellationToken)
    {
        var result = await _handler.GetPayment(id, cancellationToken);
        return result.Match(Ok, errors => Problem(errors));
    }

    [HttpGet]
    [ProducesResponseType<PagedResponse<PaymentResponse>>(StatusCodes.Status200OK)]
    public async Task<IActionResult> List(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20,
        CancellationToken cancellationToken = default)
    {
        var result = await _handler.ListPayments(page, pageSize, cancellationToken);
        return Ok(result);
    }
}
```

## Minimal API Pattern

```csharp
var payments = app.MapGroup("api/v{version:apiVersion}/payments")
    .WithApiVersionSet(versionSet)
    .MapToApiVersion(1, 0);

payments.MapPost("/", async Task<Results<Created<PaymentResponse>, Conflict<ProblemDetails>>> (
    [FromBody] CreatePaymentRequest request,
    [FromHeader(Name = "Idempotency-Key")] string idempotencyKey,
    IPaymentHandler handler,
    CancellationToken cancellationToken) =>
{
    var result = await handler.CreatePayment(request.ToCommand(idempotencyKey), cancellationToken);

    return result.Match<Results<Created<PaymentResponse>, Conflict<ProblemDetails>>>(
        payment => TypedResults.Created($"/api/v1/payments/{payment.Id}", payment),
        errors => TypedResults.Conflict(errors.ToProblemDetails())
    );
})
.WithName("CreatePayment")
.Produces<PaymentResponse>(StatusCodes.Status201Created)
.ProducesProblem(StatusCodes.Status409Conflict);

payments.MapGet("/{id:long}", async Task<Results<Ok<PaymentResponse>, NotFound>> (
    long id,
    IPaymentHandler handler,
    CancellationToken cancellationToken) =>
{
    var result = await handler.GetPayment(id, cancellationToken);

    return result.Match<Results<Ok<PaymentResponse>, NotFound>>(
        payment => TypedResults.Ok(payment),
        _ => TypedResults.NotFound()
    );
});
```

## Request / Response Models

```csharp
// Request: record with validation at the boundary
public record CreatePaymentRequest(
    long SourceAccountId,
    long DestinationAccountId,
    decimal Amount,
    string Currency);

// Validator (FluentValidation or DataAnnotations — follow CONVENTIONS.md)
public class CreatePaymentRequestValidator : AbstractValidator<CreatePaymentRequest>
{
    public CreatePaymentRequestValidator()
    {
        RuleFor(x => x.Amount).GreaterThan(0).WithMessage("Amount must be positive");
        RuleFor(x => x.Currency).Length(3).WithMessage("Currency must be ISO 4217 code");
        RuleFor(x => x.SourceAccountId).NotEqual(x => x.DestinationAccountId)
            .WithMessage("Cannot transfer to same account");
    }
}

// Response: record, no internal details
public record PaymentResponse(
    long Id,
    long SourceAccountId,
    long DestinationAccountId,
    decimal Amount,
    string Currency,
    string Status,
    DateTimeOffset CreatedAt);
```

## ProblemDetails Setup

Configure ProblemDetails globally. Cross-reference `error-handling` skill for error type mapping.

```csharp
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = context =>
    {
        context.ProblemDetails.Extensions["correlationId"] = context.HttpContext.TraceIdentifier;
    };
});
```

## Versioning

**Prefer URL path versioning** — clearest for consumers, visible in logs, easy to route.

```csharp
builder.Services.AddApiVersioning(options =>
{
    options.DefaultApiVersion = new ApiVersion(1, 0);
    options.AssumeDefaultVersionWhenUnspecified = true;
    options.ReportApiVersions = true;
})
.AddApiExplorer(options =>
{
    options.GroupNameFormat = "'v'VVV";
    options.SubstituteApiVersionInUrl = true;
});
```

**When to version:**
- Removing or renaming fields in response models
- Changing the meaning of existing fields
- Removing endpoints
- Changing validation rules that would reject previously valid requests

**When NOT to version:**
- Adding new optional fields to responses
- Adding new endpoints
- Bug fixes that correct behaviour to match documentation

## Pagination

```csharp
// Standard pagination parameters
public record PaginationParams(int Page = 1, int PageSize = 20)
{
    public int Page { get; init; } = Math.Max(1, Page);
    public int PageSize { get; init; } = Math.Clamp(PageSize, 1, 100);
}

// Standard response envelope
public record PagedResponse<T>(
    IReadOnlyList<T> Items,
    int Page,
    int PageSize,
    int TotalCount,
    int TotalPages);
```

## Resilience & Auditability Rules

1. **Idempotency keys for mutations** — All `POST`/`PUT`/`PATCH` endpoints that create or modify critical data must accept an `Idempotency-Key` header
2. **Rate limiting** — Mutation endpoints must have rate limiting configured (consult `aspnet-middleware` skill)
3. **Audit logging** — All mutation endpoints must produce audit log entries (who, what, when, from where)
4. **No PII in URLs** — Account numbers, sort codes, names must never appear in URL paths or query strings (use request body or path IDs only)
5. **Consistent error codes** — Use domain-specific error codes from the `error-handling` skill

## Review Checklist

### Endpoint Design

- [ ] Resource-based paths (nouns, not verbs)?
- [ ] Correct HTTP methods (GET for reads, POST for creates, etc.)?
- [ ] Correct HTTP status codes for success and error cases?
- [ ] CancellationToken on all async endpoints?
- [ ] Consistent with API style in CONVENTIONS.md (Controllers or Minimal APIs)?

### Error Handling

- [ ] ProblemDetails (RFC 9457) for all error responses?
- [ ] Correlation ID in error responses?
- [ ] No 200-with-error-body pattern?
- [ ] Error codes from `error-handling` skill?

### Request/Response

- [ ] Validation at the API boundary (FluentValidation or DataAnnotations)?
- [ ] Records used for request/response DTOs?
- [ ] No internal details in responses (entity IDs OK, connection strings not OK)?
- [ ] Collections paginated with standard envelope?

### Resilience & Auditability

- [ ] Idempotency-Key header on mutation endpoints?
- [ ] No PII in URLs?
- [ ] Audit logging for mutations?
- [ ] Rate limiting configured?
- [ ] Versioned if breaking changes introduced?
