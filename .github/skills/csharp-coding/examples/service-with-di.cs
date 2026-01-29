// Example: Service with Constructor Injection
// This demonstrates the standard pattern for services in our codebase.

public sealed class PaymentService : IPaymentService
{
    private readonly IPaymentRepository _repository;
    private readonly IAccountService _accountService;
    private readonly IDateTimeProvider _dateTime;
    private readonly ILogger<PaymentService> _logger;

    public PaymentService(
        IPaymentRepository repository,
        IAccountService accountService,
        IDateTimeProvider dateTime,
        ILogger<PaymentService> logger)
    {
        _repository = repository;
        _accountService = accountService;
        _dateTime = dateTime;
        _logger = logger;
    }

    public async Task<Result<PaymentId>> ProcessPaymentAsync(
        ProcessPaymentCommand command,
        CancellationToken ct)
    {
        // Validate inputs at boundary
        ArgumentNullException.ThrowIfNull(command);
        ct.ThrowIfCancellationRequested();

        _logger.LogInformation(
            "Processing payment {PaymentId} for account {AccountId}",
            command.PaymentId,
            command.AccountId);

        // Check account exists and is active
        var account = await _accountService.GetByIdAsync(command.AccountId, ct);
        if (account is null)
            return Result.Failure<PaymentId>(PaymentErrors.AccountNotFound(command.AccountId));

        if (!account.IsActive)
            return Result.Failure<PaymentId>(PaymentErrors.AccountInactive(command.AccountId));

        // Create payment entity
        var payment = Payment.Create(
            command.PaymentId,
            command.AccountId,
            command.Amount,
            _dateTime.UtcNow);

        // Persist
        await _repository.AddAsync(payment, ct);

        _logger.LogInformation(
            "Payment {PaymentId} processed successfully",
            payment.Id);

        return Result.Success(payment.Id);
    }
}
