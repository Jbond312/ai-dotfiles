// Example: CQRS Handler Pattern (MediatR style)
// Use this structure for command/query handlers with CQRS and MediatR.

// --- Command Definition ---
public sealed record ProcessInterestCommand(
    AccountId AccountId,
    DateOnly CalculationDate,
    string IdempotencyKey) : IRequest<Result<InterestPosting>>;

// --- Handler ---
public sealed class ProcessInterestCommandHandler
    : IRequestHandler<ProcessInterestCommand, Result<InterestPosting>>
{
    private readonly IAccountRepository _accountRepository;
    private readonly IInterestCalculator _interestCalculator;
    private readonly IDateTimeProvider _dateTime;
    private readonly ILogger<ProcessInterestCommandHandler> _logger;

    public ProcessInterestCommandHandler(
        IAccountRepository accountRepository,
        IInterestCalculator interestCalculator,
        IDateTimeProvider dateTime,
        ILogger<ProcessInterestCommandHandler> logger)
    {
        _accountRepository = accountRepository;
        _interestCalculator = interestCalculator;
        _dateTime = dateTime;
        _logger = logger;
    }

    public async Task<Result<InterestPosting>> Handle(
        ProcessInterestCommand request,
        CancellationToken ct)
    {
        _logger.LogInformation(
            "Processing interest for account {AccountId} on {Date}",
            request.AccountId,
            request.CalculationDate);

        // Load aggregate
        var account = await _accountRepository.FindByIdAsync(request.AccountId, ct);
        if (account is null)
            return Result.Failure<InterestPosting>(AccountErrors.NotFound(request.AccountId));

        // Calculate interest (domain logic)
        var interestAmount = _interestCalculator.Calculate(
            account.Balance,
            account.InterestRate,
            request.CalculationDate);

        if (interestAmount <= 0)
        {
            _logger.LogInformation(
                "No interest to post for account {AccountId}",
                request.AccountId);
            return Result.Success(InterestPosting.None);
        }

        // Apply to aggregate
        var posting = account.PostInterest(
            interestAmount,
            request.CalculationDate,
            request.IdempotencyKey,
            _dateTime.UtcNow);

        // Persist
        await _accountRepository.UpdateAsync(account, ct);

        _logger.LogInformation(
            "Posted interest {Amount:C} to account {AccountId}",
            interestAmount,
            request.AccountId);

        return Result.Success(posting);
    }
}

// --- Validator (FluentValidation) ---
public sealed class ProcessInterestCommandValidator
    : AbstractValidator<ProcessInterestCommand>
{
    public ProcessInterestCommandValidator()
    {
        RuleFor(x => x.AccountId)
            .NotEmpty()
            .WithMessage("Account ID is required");

        RuleFor(x => x.CalculationDate)
            .NotEmpty()
            .LessThanOrEqualTo(DateOnly.FromDateTime(DateTime.UtcNow))
            .WithMessage("Calculation date cannot be in the future");

        RuleFor(x => x.IdempotencyKey)
            .NotEmpty()
            .MaximumLength(100)
            .WithMessage("Idempotency key is required");
    }
}
