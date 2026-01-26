---
name: code-reviewing
description: "Review code for quality, correctness, and pattern adherence. Use when reviewing code before commit, validating implementation quality, checking for anti-patterns, or flagging external dependencies. Triggers on: review, code review, check code, validate, before commit, external dependency, stored procedure, ready to commit."
---

# Code Review Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for repository-specific patterns. Compare changes against these conventions.

## Hard Rules for Review

### Must Flag as Critical

1. **Data integrity risks** — Missing transactions, race conditions, partial updates
2. **Security issues** — SQL injection, missing auth checks, logged secrets
3. **Breaking changes** — API contracts, database schemas, message formats
4. **Missing error handling** — Unhandled exceptions in critical paths
5. **External dependency changes** — New stored procs, API calls, service dependencies

### Must Flag as Important

1. **Pattern violations** — Code doesn't match CONVENTIONS.md
2. **Missing tests** — New behaviour without corresponding test
3. **Non-deterministic code** — DateTime.Now, Random without seed
4. **Tight coupling** — Direct instantiation instead of DI
5. **Magic values** — Hardcoded strings, numbers without constants

## Review Checklist

### 1. Correctness

- [ ] Does the code implement what the PLAN.md specifies?
- [ ] Are all edge cases from the plan handled?
- [ ] Do error paths return appropriate responses?
- [ ] Is null handling explicit and correct?

### 2. Tests

- [ ] Do tests exist for each new behaviour?
- [ ] Do tests follow TDD (written before implementation)?
- [ ] Are assertions specific, not just "doesn't throw"?
- [ ] Do tests follow naming convention from CONVENTIONS.md?

### 3. Patterns

- [ ] Does code match patterns in CONVENTIONS.md?
- [ ] Is code in the correct location (layer, folder)?
- [ ] Are naming conventions followed?
- [ ] Is the approach consistent with similar code in the repo?

### 4. Banking Domain

- [ ] Is the operation idempotent (can be safely retried)?
- [ ] Are state changes auditable?
- [ ] Is input validated at system boundaries?
- [ ] Are financial calculations using `decimal`?
- [ ] Is sensitive data excluded from logs?

### 5. External Dependencies

- [ ] Any new stored procedure calls?
- [ ] Any new external API calls?
- [ ] Any new database tables/columns?
- [ ] Any new message queue interactions?

## Issue Severity

| Severity       | Description                                      | Examples                                            | Action                  |
| -------------- | ------------------------------------------------ | --------------------------------------------------- | ----------------------- |
| **Critical**   | Breaks functionality, data integrity, security   | Missing null check on payment amount, SQL injection | Must fix before merge   |
| **Important**  | Maintainability, testability, pattern violations | Using DateTime.Now, missing DI                      | Should fix before merge |
| **Suggestion** | Style, minor improvements                        | Variable naming, comment clarity                    | Can defer to follow-up  |
| **External**   | Requires human verification                      | New stored proc, external API                       | Flag for team review    |

## Good vs Bad Examples

### Null Handling

```csharp
// ❌ BAD: Silent null that will cause issues downstream
public decimal CalculateTotal(Order order)
{
    return order.Items.Sum(i => i.Price * i.Quantity);  // NullReferenceException if Items is null
}

// ✅ GOOD: Explicit null handling
public decimal CalculateTotal(Order order)
{
    ArgumentNullException.ThrowIfNull(order);

    if (order.Items is null or { Count: 0 })
        return 0m;

    return order.Items.Sum(i => i.Price * i.Quantity);
}
```

### Error Handling

```csharp
// ❌ BAD: Swallowing exception
try
{
    await _paymentGateway.ChargeAsync(payment);
}
catch (Exception)
{
    return Result.Failure("Payment failed");  // Lost all diagnostic info
}

// ✅ GOOD: Proper exception handling
try
{
    await _paymentGateway.ChargeAsync(payment);
}
catch (PaymentGatewayException ex) when (ex.IsRetryable)
{
    _logger.LogWarning(ex, "Retryable payment failure for {PaymentId}", payment.Id);
    throw new PaymentProcessingException("Payment failed, please retry", ex);
}
catch (PaymentGatewayException ex)
{
    _logger.LogError(ex, "Non-retryable payment failure for {PaymentId}", payment.Id);
    throw new PaymentProcessingException("Payment failed permanently", ex);
}
```

### Idempotency

```csharp
// ❌ BAD: Not idempotent - will create duplicates
public async Task ProcessPaymentAsync(PaymentRequest request)
{
    var payment = new Payment(request.Amount, request.AccountId);
    await _repository.AddAsync(payment);
}

// ✅ GOOD: Idempotent with idempotency key
public async Task ProcessPaymentAsync(PaymentRequest request)
{
    var existing = await _repository.FindByIdempotencyKeyAsync(request.IdempotencyKey);
    if (existing is not null)
    {
        _logger.LogInformation("Duplicate request {Key}, returning existing result", request.IdempotencyKey);
        return existing.ToResult();
    }

    var payment = new Payment(request.Amount, request.AccountId, request.IdempotencyKey);
    await _repository.AddAsync(payment);
}
```

### Logging

```csharp
// ❌ BAD: Logs sensitive data
_logger.LogInformation("Processing payment for account {AccountNumber} amount {Amount}",
    customer.AccountNumber,  // PII!
    payment.Amount);

// ✅ GOOD: Structured logging without sensitive data
_logger.LogInformation("Processing payment {PaymentId} for customer {CustomerId} amount {Amount}",
    payment.Id,
    customer.Id,  // Internal ID, not account number
    payment.Amount);
```

## External Dependency Flag Template

When external dependencies are detected, use this format:

```markdown
⚠️ **External Dependency Detected**

**Type:** {Stored Procedure | External API | Database Change | Message Queue}
**Name:** {sp_ProcessPayment | PaymentGateway.ChargeAsync | etc.}

**Verification Required:**

- [ ] Dependency exists and is accessible
- [ ] Signature/contract matches what code expects
- [ ] Error handling covers dependency's failure modes
- [ ] Timeout/retry configuration is appropriate
- [ ] Monitoring/alerting is in place

**Context:** {Brief description of why this is being called}
```

## Review Report Format

```markdown
## Code Review Summary

**Verdict:** {Approved ✅ | Changes Requested 🔄}

### PLAN.md Verification

- Implementation items: {X of Y complete}
- TDD compliance: {Yes/No/Partial}
- Verification checklist: {Complete/Incomplete}

### Issues Found

**Critical (must fix):**
{None | Numbered list with file:line references}

**Important (should fix):**
{None | Numbered list with file:line references}

**Suggestions (can defer):**
{None | Numbered list}

### External Dependencies

{None detected | List with verification checklist}

### What's Good

{Positive observations - what the code does well}
```

## Post-Review Actions

If **Approved:**

- Proceed to `committer` agent for commit

If **Changes Requested:**

- Return to `tdd-coder` or `one-shot-coder` with specific issues
- Re-review after changes are made

If **External Dependencies Flagged:**

- Pause workflow
- Present dependency list to user for human verification
- Only proceed after user confirms dependencies are valid
