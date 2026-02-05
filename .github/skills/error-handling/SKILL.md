---
name: error-handling
description: "Error handling patterns for .NET applications. Use when writing, reviewing, or deciding on error handling strategy — Result types, exceptions, ProblemDetails mapping, correlation IDs. Triggers on: error handling, Result type, OneOf, ErrorOr, ProblemDetails, exception, try/catch, error response, correlation ID."
---

# Error Handling Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's established error handling approach. The chosen approach must be followed consistently — do not mix strategies.

## Approaches Comparison

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Exceptions + middleware** | Simple, familiar, stack traces, no wrapper types | Performance cost on throw, flow control via exceptions, easy to forget catch | Small services, CRUD-heavy apps, teams familiar with .NET defaults |
| **OneOf\<TResult, TError\>** | Exhaustive matching, discriminated union, compile-time safety | Extra package dependency, verbose generic signatures, learning curve | Domain-heavy services, functional-leaning teams |
| **ErrorOr\<T\>** | Clean API, built-in error types, minimal boilerplate | Opinionated error categories, less flexible than OneOf | Rapid development, teams wanting convention over configuration |
| **FluentResults** | Rich error metadata, multiple errors per result, reasons chain | Heavier API surface, no compile-time exhaustiveness | Complex validation pipelines, batch operations |
| **Custom Result\<T\>** | Full control, no dependencies, tailored to domain | Must maintain yourself, risk of inconsistency, missing edge cases | Teams with specific requirements not met by libraries |

## Hard Rules for Review

### Must Flag as Critical

1. **Mixed approaches** — Using exceptions for flow control in some handlers and Result types in others within the same project
2. **Swallowed exceptions** — Empty `catch` blocks or `catch` blocks that only log without re-throwing or returning an error
3. **Null-for-error** — Returning `null` to indicate failure instead of using the established error pattern
4. **Log-and-throw** — Logging an exception then re-throwing it (causes duplicate log entries at every layer)
5. **Missing correlation ID** — Error responses that don't include a correlation ID for traceability

### Must Flag as Important

1. **No ProblemDetails mapping** — Errors reaching the API boundary without being mapped to RFC 9457 ProblemDetails
2. **Generic error messages** — Returning "An error occurred" without actionable detail (while still not leaking internals)
3. **Inconsistent error types** — Using different error representations in the same bounded context
4. **Missing CancellationToken** — Async error-prone operations that don't accept or propagate CancellationToken

## Result\<T\> Pattern (OneOf / ErrorOr / Custom)

```csharp
// Using ErrorOr<T> — same principle applies to OneOf or custom Result
public async Task<ErrorOr<TransferResult>> TransferFunds(
    TransferCommand command, CancellationToken cancellationToken)
{
    var sourceAccount = await _repository.GetByIdAsync(command.SourceAccountId, cancellationToken);
    if (sourceAccount is null)
        return Error.NotFound("ACCOUNT_NOT_FOUND", $"Account {command.SourceAccountId} not found");

    if (sourceAccount.Balance < command.Amount)
        return Error.Conflict("INSUFFICIENT_FUNDS", "Insufficient funds for transfer");

    return new TransferResult(sourceAccount.Id, command.Amount);
}
```

```csharp
// Controller mapping Result to HTTP response
[HttpPost("transfers")]
public async Task<IActionResult> Transfer(TransferRequest request, CancellationToken cancellationToken)
{
    var result = await _handler.TransferFunds(request.ToCommand(), cancellationToken);

    return result.Match(
        success => Ok(success),
        errors => errors.First().Type switch
        {
            ErrorType.NotFound => NotFound(ToProblemDetails(errors)),
            ErrorType.Conflict => Conflict(ToProblemDetails(errors)),
            ErrorType.Validation => BadRequest(ToProblemDetails(errors)),
            _ => StatusCode(500, ToProblemDetails(errors))
        }
    );
}
```

## ProblemDetails Mapping Reference

| Error Type | HTTP Status | RFC Type URI | Example |
|------------|-------------|--------------|---------|
| Validation failure | 400 Bad Request | `https://tools.ietf.org/html/rfc9110#section-15.5.1` | Invalid amount format |
| Authentication | 401 Unauthorized | `https://tools.ietf.org/html/rfc9110#section-15.5.2` | Missing/invalid token |
| Authorization | 403 Forbidden | `https://tools.ietf.org/html/rfc9110#section-15.5.4` | Insufficient permissions |
| Not found | 404 Not Found | `https://tools.ietf.org/html/rfc9110#section-15.5.5` | Account not found |
| Conflict / business rule | 409 Conflict | `https://tools.ietf.org/html/rfc9110#section-15.5.10` | Insufficient funds, duplicate |
| Unprocessable | 422 Unprocessable Entity | `https://tools.ietf.org/html/rfc4918#section-11.2` | Valid format, invalid business state |
| Rate limited | 429 Too Many Requests | `https://tools.ietf.org/html/rfc6585#section-4` | Rate limit exceeded |
| Internal error | 500 Internal Server Error | `https://tools.ietf.org/html/rfc9110#section-15.6.1` | Unhandled exception |

## Resilience & Auditability Rules

1. **Critical operation errors must be auditable** — Every error that affects a critical operation (failed transfer, declined payment, balance discrepancy) must produce an audit record, not just a log entry
2. **Domain-specific error codes** — Use domain-specific codes (`INSUFFICIENT_FUNDS`, `ACCOUNT_FROZEN`, `DUPLICATE_PAYMENT`) not generic HTTP descriptions
3. **Idempotent duplicates are not errors** — A duplicate request with the same idempotency key should return the original successful response, not a 409 Conflict
4. **No internal details in error responses** — Stack traces, connection strings, SQL errors, internal identifiers must never appear in API responses
5. **Correlation ID propagation** — Every error response must include a correlation ID that traces through logs, downstream services, and audit records

## Review Checklist

### Approach Consistency

- [ ] Single error handling approach used throughout the project?
- [ ] New code follows the approach documented in CONVENTIONS.md?
- [ ] No mixing of exceptions-for-flow-control and Result types in the same bounded context?

### Error Responses

- [ ] All API errors return ProblemDetails (RFC 9457)?
- [ ] Correlation ID included in error responses?
- [ ] No internal details leaked (stack traces, SQL errors, connection strings)?
- [ ] Error codes are domain-specific and documented?

### Exception Handling

- [ ] No empty catch blocks?
- [ ] No log-and-throw (log at boundary only)?
- [ ] No null-for-error returns?
- [ ] CancellationToken propagated through async chains?
- [ ] OperationCanceledException handled appropriately (not logged as error)?

### Resilience & Auditability

- [ ] Critical operation errors produce audit records?
- [ ] Idempotent operations return original result on duplicate (not error)?
- [ ] Error codes are domain-specific and meaningful?
- [ ] Sensitive data excluded from error messages?
