---
name: azure-service-bus
description: "Azure Service Bus messaging patterns for .NET applications. Use when writing, reviewing, or debugging message producers, consumers, dead-letter handling, or Service Bus configuration. Triggers on: Service Bus, ServiceBusClient, ServiceBusProcessor, message queue, topic, subscription, dead-letter, message handler, messaging."
---

# Azure Service Bus Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's messaging patterns. Follow established message contract and handler conventions.

## Hard Rules for Review

### Must Flag as Critical

1. **Non-idempotent handlers** — Message processors that don't guard against duplicate delivery (at-least-once semantics means duplicates will happen)
2. **Missing `ProcessErrorAsync`** — `ServiceBusProcessor` without error handler configured, causing silent failures
3. **Unstructured message contracts** — Sending anonymous objects or unversioned payloads instead of structured, versioned contracts
4. **ServiceBusClient per request** — Creating new `ServiceBusClient` instances instead of using singleton from DI
5. **Manual receive loops** — Using `ServiceBusReceiver.ReceiveMessageAsync` in a `while` loop instead of `ServiceBusProcessor`

### Must Flag as Important

1. **Missing dead-letter handling** — No DLQ monitoring or processing configured for the queue/subscription
2. **No correlation ID propagation** — Messages sent without correlation ID from the originating request
3. **Missing structured logging** — Message processing without structured log entries for traceability
4. **Hardcoded connection strings** — Service Bus connection strings outside of configuration/Key Vault

## Sending Messages

### ServiceBusSender

```csharp
// Registration — ServiceBusClient is singleton, senders are thread-safe
builder.Services.AddSingleton(sp =>
    new ServiceBusClient(sp.GetRequiredService<IConfiguration>()["ServiceBus:ConnectionString"]));

builder.Services.AddSingleton(sp =>
    sp.GetRequiredService<ServiceBusClient>().CreateSender("payment-events"));
```

```csharp
// Sending a message with properties
public class PaymentEventPublisher
{
    private readonly ServiceBusSender _sender;

    public PaymentEventPublisher(ServiceBusSender sender) => _sender = sender;

    public async Task PublishPaymentCreated(
        PaymentCreatedEvent @event,
        string correlationId,
        CancellationToken ct)
    {
        var message = new ServiceBusMessage(JsonSerializer.SerializeToUtf8Bytes(@event))
        {
            MessageId = @event.IdempotencyKey.ToString(),
            CorrelationId = correlationId,
            ContentType = "application/json",
            Subject = nameof(PaymentCreatedEvent),
            ApplicationProperties =
            {
                ["EventType"] = nameof(PaymentCreatedEvent),
                ["Version"] = "1.0"
            }
        };

        await _sender.SendMessageAsync(message, ct);
    }
}
```

## Processing Messages

### ServiceBusProcessor (Hosted Service)

```csharp
public class PaymentEventProcessor : BackgroundService
{
    private readonly ServiceBusProcessor _processor;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<PaymentEventProcessor> _logger;

    public PaymentEventProcessor(
        ServiceBusClient client,
        IServiceScopeFactory scopeFactory,
        ILogger<PaymentEventProcessor> logger)
    {
        _processor = client.CreateProcessor("payment-events", new ServiceBusProcessorOptions
        {
            MaxConcurrentCalls = 10,
            AutoCompleteMessages = false,
            PrefetchCount = 20
        });
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _processor.ProcessMessageAsync += ProcessMessageAsync;
        _processor.ProcessErrorAsync += ProcessErrorAsync;

        await _processor.StartProcessingAsync(stoppingToken);

        // Wait until cancellation requested
        await Task.Delay(Timeout.Infinite, stoppingToken).ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing);

        await _processor.StopProcessingAsync();
    }

    private async Task ProcessMessageAsync(ProcessMessageEventArgs args)
    {
        using var scope = _scopeFactory.CreateScope();
        var handler = scope.ServiceProvider.GetRequiredService<IPaymentEventHandler>();

        var correlationId = args.Message.CorrelationId;
        using var logScope = _logger.BeginScope(new Dictionary<string, object>
        {
            ["CorrelationId"] = correlationId,
            ["MessageId"] = args.Message.MessageId
        });

        try
        {
            var @event = JsonSerializer.Deserialize<PaymentCreatedEvent>(args.Message.Body);

            await handler.HandleAsync(@event!, correlationId, args.CancellationToken);

            await args.CompleteMessageAsync(args.Message, args.CancellationToken);
            _logger.LogInformation("Message {MessageId} processed successfully", args.Message.MessageId);
        }
        catch (JsonException ex)
        {
            // Permanent failure — dead-letter immediately
            _logger.LogError(ex, "Message {MessageId} has invalid payload, dead-lettering",
                args.Message.MessageId);
            await args.DeadLetterMessageAsync(args.Message, "InvalidPayload", ex.Message,
                args.CancellationToken);
        }
        catch (Exception ex)
        {
            // Transient failure — abandon for retry
            _logger.LogWarning(ex, "Message {MessageId} processing failed, abandoning for retry",
                args.Message.MessageId);
            await args.AbandonMessageAsync(args.Message, cancellationToken: args.CancellationToken);
        }
    }

    private Task ProcessErrorAsync(ProcessErrorEventArgs args)
    {
        _logger.LogError(args.Exception,
            "Service Bus error: Source={ErrorSource}, Namespace={Namespace}, Entity={EntityPath}",
            args.ErrorSource, args.FullyQualifiedNamespace, args.EntityPath);
        return Task.CompletedTask;
    }
}
```

### Complete / Abandon / Dead-Letter Decision

| Scenario | Action | Why |
|----------|--------|-----|
| Processed successfully | `CompleteMessageAsync` | Remove from queue |
| Transient failure (timeout, DB unavailable) | `AbandonMessageAsync` | Retry delivery up to MaxDeliveryCount |
| Permanent failure (invalid payload, business rule) | `DeadLetterMessageAsync` | Move to DLQ with reason |
| Duplicate (idempotency check passes) | `CompleteMessageAsync` | Already processed, safe to remove |

## Sessions for Ordered Processing

Use sessions when messages for the same entity must be processed in order (e.g., account transactions).

```csharp
// Sending with session ID
var message = new ServiceBusMessage(body)
{
    SessionId = accountId.ToString(), // Messages for same account processed in order
    MessageId = idempotencyKey.ToString()
};

// Processing with sessions
var processor = client.CreateSessionProcessor("account-transactions",
    new ServiceBusSessionProcessorOptions
    {
        MaxConcurrentSessions = 10,
        AutoCompleteMessages = false
    });
```

## Message Design

### Envelope Pattern

```csharp
// Versioned message contract
public record PaymentCreatedEvent
{
    public required Guid EventId { get; init; }
    public required string EventType { get; init; }
    public required string Version { get; init; }
    public required DateTimeOffset Timestamp { get; init; }
    public required string CorrelationId { get; init; }
    public required PaymentCreatedPayload Payload { get; init; }
}

public record PaymentCreatedPayload
{
    public required long PaymentId { get; init; }
    public required long SourceAccountId { get; init; }
    public required long DestinationAccountId { get; init; }
    public required decimal Amount { get; init; }
    public required string Currency { get; init; }
}
```

## Resilience & Auditability Rules

1. **Sessions keyed by entity ID** — Use `SessionId = entityId.ToString()` for ordered processing of entity-specific events (e.g., account transfers, balance updates)
2. **Idempotency key + DB check** — Set `MessageId` to the idempotency key, AND check the database for prior processing. `MessageId`-based deduplication has a limited window
3. **Correlation ID propagation** — Every message must carry the originating request's correlation ID through `CorrelationId` property
4. **Audit logging** — Log message receipt, processing outcome, and completion/dead-letter action with structured fields
5. **Encrypt sensitive body data** — If message payloads contain PII or sensitive details, encrypt the body (Service Bus transport is TLS, but messages at rest in queues may be accessible)

## Review Checklist

### Client & Configuration

- [ ] `ServiceBusClient` registered as singleton?
- [ ] Connection string from configuration/Key Vault (not hardcoded)?
- [ ] Retry policy configured appropriately?
- [ ] `ServiceBusProcessor` used (not manual receive loops)?

### Sending

- [ ] Messages have `MessageId` set (for deduplication)?
- [ ] `CorrelationId` propagated from originating request?
- [ ] Message contracts are structured and versioned?
- [ ] `CancellationToken` propagated to send operations?

### Processing

- [ ] `ProcessErrorAsync` handler configured?
- [ ] `AutoCompleteMessages = false` (explicit complete/abandon)?
- [ ] Handlers are idempotent (duplicate delivery safe)?
- [ ] Transient vs permanent failures distinguished?
- [ ] Dead-letter used for permanent failures with reason?
- [ ] Scoped DI used for message handlers?

### Dead-Letter

- [ ] DLQ monitoring configured?
- [ ] Dead-letter reasons and descriptions set when dead-lettering?
- [ ] Health check includes DLQ depth?

### Resilience & Auditability

- [ ] Sessions used for ordered entity-specific processing?
- [ ] Idempotency checked at both message and database level?
- [ ] Correlation ID present on all messages?
- [ ] Audit trail for message processing?
- [ ] Sensitive data encrypted in message body?
