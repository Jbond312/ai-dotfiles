// Example: Result Pattern for Error Handling
// Use this pattern when errors are expected outcomes, not exceptions.

// --- Domain Errors ---
public static class AccountErrors
{
    public static Error NotFound(AccountId id) =>
        new("Account.NotFound", $"Account {id} was not found");

    public static Error InsufficientFunds(AccountId id, decimal required, decimal available) =>
        new("Account.InsufficientFunds", 
            $"Account {id} has insufficient funds. Required: {required:C}, Available: {available:C}");

    public static Error Frozen(AccountId id) =>
        new("Account.Frozen", $"Account {id} is frozen and cannot process transactions");
}

// --- Service Method Using Result ---
public async Task<Result<WithdrawalReceipt>> WithdrawAsync(
    AccountId accountId,
    decimal amount,
    string idempotencyKey,
    CancellationToken ct)
{
    // Idempotency check
    var existing = await _repository.FindByIdempotencyKeyAsync(idempotencyKey, ct);
    if (existing is not null)
        return Result.Success(existing.ToReceipt()); // Already processed

    // Load account
    var account = await _repository.FindByIdAsync(accountId, ct);
    if (account is null)
        return Result.Failure<WithdrawalReceipt>(AccountErrors.NotFound(accountId));

    // Business rule checks
    if (account.IsFrozen)
        return Result.Failure<WithdrawalReceipt>(AccountErrors.Frozen(accountId));

    if (account.AvailableBalance < amount)
        return Result.Failure<WithdrawalReceipt>(
            AccountErrors.InsufficientFunds(accountId, amount, account.AvailableBalance));

    // Execute withdrawal
    var withdrawal = account.Withdraw(amount, idempotencyKey, _dateTime.UtcNow);
    await _repository.UpdateAsync(account, ct);

    return Result.Success(withdrawal.ToReceipt());
}

// --- Controller Mapping Results to HTTP ---
[HttpPost]
public async Task<IActionResult> Withdraw(
    [FromBody] WithdrawRequest request,
    CancellationToken ct)
{
    var result = await _accountService.WithdrawAsync(
        new AccountId(request.AccountId),
        request.Amount,
        request.IdempotencyKey,
        ct);

    return result.Match(
        onSuccess: receipt => Ok(receipt),
        onFailure: error => error.Code switch
        {
            "Account.NotFound" => NotFound(error.Message),
            "Account.InsufficientFunds" => UnprocessableEntity(error.Message),
            "Account.Frozen" => Conflict(error.Message),
            _ => BadRequest(error.Message)
        });
}
