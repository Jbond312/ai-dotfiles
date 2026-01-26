---
name: csharp-coding
description: "C# coding standards, patterns, and best practices for .NET development. Use when writing C# code, implementing features, creating classes, or reviewing code quality. Triggers on: C#, .NET, implement, create class, add method, handler, service, write code."
---

# C# Coding Standards

**Before writing code:** Read `.planning/CONVENTIONS.md` for repository-specific patterns. If it doesn't exist, ask to run the `repo-analyzer` skill first.

## Hard Rules

### Must

1. **Follow repository conventions** — Check `.planning/CONVENTIONS.md` for this repo's specific patterns
2. **Use the existing test framework** — Don't introduce new test libraries
3. **Match existing code style** — Namespaces, formatting, naming should be consistent
4. **Handle nulls explicitly** — Use nullable reference types, null checks, or Option/Maybe patterns
5. **Make dependencies explicit** — Inject via constructor, never use service locator
6. **Validate inputs at boundaries** — Public methods and API endpoints must validate

### Must Not

1. **DateTime.Now / DateTime.UtcNow** — Use injected `IDateTimeProvider` or `TimeProvider` for testability
2. **Catch generic Exception without re-throwing** — Catch specific exceptions or re-throw after logging
3. **Magic strings for configuration** — Use strongly-typed options pattern
4. **Public fields** — Use properties, even for simple DTOs
5. **Static state** — Avoid static mutable state; use DI scopes instead
6. **Hardcoded connection strings or secrets** — Use configuration/secrets management

## Soft Rules (Prefer / Avoid)

### Prefer

- Records for immutable DTOs and value objects
- Primary constructors for simple classes (if repo uses them)
- Expression-bodied members for single-line methods
- Collection expressions `[a, b, c]` over `new List<T> { a, b, c }`
- Pattern matching over type checks and casts
- `sealed` on classes not designed for inheritance

### Avoid

- Regions (`#region`) — they hide complexity
- Multiple classes per file (except nested private classes)
- Deep inheritance hierarchies — prefer composition
- Overuse of extension methods — they're hard to mock
- Comments that explain _what_ — code should be self-documenting; comments explain _why_

## Golden Examples

### Constructor Injection (Correct)

```csharp
public sealed class OrderService
{
    private readonly IOrderRepository _repository;
    private readonly IDateTimeProvider _dateTime;
    private readonly ILogger<OrderService> _logger;

    public OrderService(
        IOrderRepository repository,
        IDateTimeProvider dateTime,
        ILogger<OrderService> logger)
    {
        _repository = repository;
        _dateTime = dateTime;
        _logger = logger;
    }
}
```

### Result Pattern (When Used in Repo)

```csharp
public async Task<Result<Order>> GetOrderAsync(OrderId id, CancellationToken ct)
{
    var order = await _repository.FindByIdAsync(id, ct);

    if (order is null)
        return Result.Failure<Order>(OrderErrors.NotFound(id));

    if (order.IsArchived)
        return Result.Failure<Order>(OrderErrors.Archived(id));

    return Result.Success(order);
}
```

### Guard Clauses

```csharp
public void ProcessPayment(Payment payment, decimal amount)
{
    ArgumentNullException.ThrowIfNull(payment);
    ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount);

    // Main logic follows...
}
```

### Async Method Structure

```csharp
public async Task<CustomerDto> GetCustomerAsync(CustomerId id, CancellationToken ct)
{
    ct.ThrowIfCancellationRequested();

    var customer = await _repository.FindByIdAsync(id, ct)
        ?? throw new CustomerNotFoundException(id);

    return customer.ToDto();
}
```

## Anti-Patterns (Don't Do This)

### ❌ Service Locator

```csharp
// BAD: Hidden dependency, untestable
public void Process()
{
    var service = ServiceLocator.Get<IOrderService>();
    service.DoSomething();
}
```

**Why it's bad:** Dependencies are hidden, testing requires static setup, violations of DI principles.

### ❌ Swallowing Exceptions

```csharp
// BAD: Errors disappear silently
try
{
    await ProcessPaymentAsync();
}
catch (Exception)
{
    // Swallowed - we'll never know it failed
}
```

**Why it's bad:** Failures go undetected, debugging becomes impossible, data integrity at risk.

### ❌ DateTime.Now in Business Logic

```csharp
// BAD: Untestable, non-deterministic
public bool IsExpired() => ExpiryDate < DateTime.Now;
```

**Why it's bad:** Can't write reliable tests, time zone issues, non-deterministic behaviour.

### ❌ Stringly-Typed Code

```csharp
// BAD: No compile-time safety
var status = order.GetProperty("Status");
if (status == "completed") { ... }
```

**Why it's bad:** Typos cause runtime errors, no refactoring support, no IntelliSense.

## Banking-Specific Rules

### Financial Calculations

- Use `decimal` for money, never `double` or `float`
- Be explicit about rounding: `Math.Round(amount, 2, MidpointRounding.ToEven)`
- Document rounding rules in comments when they're domain-specific

### Idempotency

- Operations that can be retried must be idempotent
- Use idempotency keys for external API calls
- Check for existing records before insert in upsert scenarios

### Audit Trail

- State changes on sensitive entities should be logged
- Include correlation IDs in all log entries
- Never log sensitive data (account numbers, PII) in plain text

## Verification Checklist

Before considering code complete:

- [ ] Follows patterns in `.planning/CONVENTIONS.md`
- [ ] No compiler warnings introduced
- [ ] Null handling is explicit
- [ ] All public methods have XML docs (if repo convention)
- [ ] No magic numbers or strings
- [ ] Async methods accept `CancellationToken`
- [ ] Dependencies are injected, not resolved
