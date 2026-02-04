---
name: security-review
description: "Security review checklist for .NET banking applications. Use when reviewing code for security concerns, checking for OWASP vulnerabilities, or validating data protection in financial services code."
---

# Security Review Checklist

Use this checklist alongside the `code-reviewing` skill. Security issues are always **Critical** severity.

## Injection

- [ ] No string concatenation in SQL queries — use parameterised queries or ORM
- [ ] No raw user input in dynamic LINQ, `Expression.Compile()`, or `Activator.CreateInstance()`
- [ ] Command arguments are validated and sanitised before shell execution
- [ ] No user input interpolated into log message templates (use structured logging placeholders)

```csharp
// BAD: SQL injection
var sql = $"SELECT * FROM Accounts WHERE Id = '{request.AccountId}'";

// GOOD: Parameterised
var account = await _context.Accounts.FindAsync(request.AccountId);
```

## Authentication & Authorisation

- [ ] Endpoints have appropriate `[Authorize]` attributes or policy checks
- [ ] No authorisation logic bypassed by checking user identity in business logic instead of middleware
- [ ] API keys and tokens are not hardcoded
- [ ] Service-to-service calls use managed identity or certificate auth, not shared secrets

## Sensitive Data Exposure

- [ ] No PII in logs (account numbers, sort codes, names, addresses, email, phone)
- [ ] Use internal IDs (CustomerId, PaymentId) in logs, not real-world identifiers
- [ ] Sensitive fields excluded from serialisation where appropriate (`[JsonIgnore]`, DTOs)
- [ ] Connection strings and secrets loaded from configuration/Key Vault, never hardcoded
- [ ] Error responses don't leak stack traces, internal paths, or database details to clients

```csharp
// BAD: PII in logs
_logger.LogInformation("Transfer from {AccountNumber} to {DestAccount}", source.AccountNumber, dest.AccountNumber);

// GOOD: Internal IDs only
_logger.LogInformation("Transfer {TransferId} from account {SourceId} to {DestId}", transfer.Id, source.Id, dest.Id);
```

## Input Validation

- [ ] All public API inputs validated at the boundary (FluentValidation, DataAnnotations, or guard clauses)
- [ ] Numeric ranges checked (no negative amounts, no amounts exceeding limits)
- [ ] String lengths bounded (no unbounded text fields)
- [ ] Enum values validated (not just cast from int)
- [ ] File uploads validated for type, size, and content if applicable

## Financial Integrity

- [ ] Money uses `decimal`, never `double` or `float`
- [ ] Rounding rules explicit and documented (`MidpointRounding.ToEven` or business-specified)
- [ ] Operations are idempotent — duplicate requests produce the same result, not duplicate effects
- [ ] State changes are transactional — no partial updates on failure
- [ ] Concurrent access handled (optimistic concurrency, row versioning, or explicit locking)

```csharp
// BAD: Not idempotent, race condition
public async Task DebitAsync(Guid accountId, decimal amount)
{
    var account = await _repo.GetAsync(accountId);
    account.Balance -= amount;
    await _repo.SaveAsync(account);
}

// GOOD: Idempotent with concurrency check
public async Task<Result> DebitAsync(DebitCommand command)
{
    var existing = await _repo.FindByIdempotencyKeyAsync(command.IdempotencyKey);
    if (existing is not null) return Result.Ok();

    var account = await _repo.GetAsync(command.AccountId);
    account.Debit(command.Amount); // Domain validates balance
    await _repo.SaveAsync(account); // Concurrency token checked
}
```

## Cryptography & Secrets

- [ ] No custom cryptography implementations — use framework-provided APIs
- [ ] Secrets not stored in source code, config files, or environment variables in production
- [ ] API keys rotated via Key Vault or similar, not baked into deployments
- [ ] Hashing uses appropriate algorithms (SHA-256+ for integrity, bcrypt/Argon2 for passwords)

## Error Handling & Information Leakage

- [ ] Exception details not returned to API clients (use problem details with safe messages)
- [ ] Catch blocks don't swallow exceptions silently in security-critical paths
- [ ] Failed authentication/authorisation returns generic messages (not "user not found" vs "wrong password")
- [ ] Rate limiting considered for authentication and high-value operations

## Audit & Traceability

- [ ] State changes on financial entities raise domain events or write audit records
- [ ] Audit records include: who, what, when, correlation ID
- [ ] Audit records are immutable (append-only)
- [ ] Correlation IDs propagated across service boundaries

## Dependency Security

- [ ] No known-vulnerable NuGet packages (check for advisories)
- [ ] Third-party packages from trusted sources
- [ ] Minimal permissions granted to service accounts and managed identities

## Review Report Format

When security issues are found, add a dedicated section to the review report:

```markdown
### Security Issues

**Critical:**
1. {file:line} — {description of vulnerability and remediation}

**Advisory:**
1. {file:line} — {recommendation for hardening}
```

Security issues flagged as **Critical** are blockers — they must be fixed before merge.
