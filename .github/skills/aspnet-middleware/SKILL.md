---
name: aspnet-middleware
description: "ASP.NET middleware pipeline standards for .NET applications. Use when writing, reviewing, or configuring middleware — exception handling, correlation IDs, request logging, health checks, pipeline ordering. Triggers on: middleware, pipeline, UseExceptionHandler, health check, correlation ID, request logging, UseRouting, UseAuthentication."
---

# ASP.NET Middleware Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's middleware conventions. Follow the established patterns for pipeline configuration.

## Hard Rules for Review

### Must Flag as Critical

1. **Wrong middleware ordering** — Authentication after Authorization, exception handler not first, routing after endpoints
2. **Missing centralized exception handling** — No `UseExceptionHandler` or equivalent, allowing raw exceptions to reach clients
3. **No correlation ID** — Requests processed without generating or propagating a correlation ID
4. **Missing health checks** — No health check endpoints for dependent services (database, message bus)

### Must Flag as Important

1. **`next()` called multiple times** — Middleware invoking `next(context)` more than once, causing double-processing
2. **Missing CancellationToken propagation** — Custom middleware not respecting `context.RequestAborted`
3. **Logging sensitive data** — Request/response logging that captures authentication tokens, PII, or financial details
4. **Synchronous I/O in middleware** — Blocking calls in the request pipeline

## Pipeline Order

The order of middleware registration matters. Follow this ordering:

```
Request
  │
  ├─ 1. Exception Handler        ← Catches all downstream exceptions
  ├─ 2. HSTS                     ← Strict transport security headers
  ├─ 3. HTTPS Redirection        ← Redirect HTTP to HTTPS
  ├─ 4. Correlation ID           ← Generate/read correlation ID (custom)
  ├─ 5. Request Logging          ← Log request summary (custom)
  ├─ 6. Routing                  ← Match request to endpoint
  ├─ 7. Rate Limiting            ← Throttle requests
  ├─ 8. Authentication           ← Identify the caller
  ├─ 9. Authorization            ← Check permissions
  ├─ 10. Custom Middleware       ← Business-specific middleware
  └─ 11. Endpoints               ← Execute matched endpoint
  │
Response
```

```csharp
var app = builder.Build();

// 1. Exception handling — MUST be first
app.UseExceptionHandler();

// 2-3. Transport security
if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}
app.UseHttpsRedirection();

// 4-5. Observability (custom middleware)
app.UseCorrelationId();
app.UseRequestLogging();

// 6. Routing
app.UseRouting();

// 7. Rate limiting
app.UseRateLimiter();

// 8-9. Auth
app.UseAuthentication();
app.UseAuthorization();

// 10. Health checks (before endpoints, after auth if health checks need auth)
app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});
app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false // Liveness = "is the process running?"
});

// 11. Endpoints
app.MapControllers();
```

## Exception Handling Middleware

Cross-reference `error-handling` skill for error type mapping and ProblemDetails structure.

### Built-in UseExceptionHandler

```csharp
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = context =>
    {
        context.ProblemDetails.Extensions["correlationId"] = context.HttpContext.TraceIdentifier;
        // Never expose internal details in production
        if (!context.HttpContext.RequestServices.GetRequiredService<IHostEnvironment>().IsDevelopment())
        {
            context.ProblemDetails.Detail = null;
        }
    };
});

app.UseExceptionHandler();
app.UseStatusCodePages();
```

### Custom Exception Handler

```csharp
// For more control over error mapping
app.UseExceptionHandler(appBuilder =>
{
    appBuilder.Run(async context =>
    {
        var exception = context.Features.Get<IExceptionHandlerFeature>()?.Error;
        var logger = context.RequestServices.GetRequiredService<ILogger<Program>>();

        logger.LogError(exception, "Unhandled exception for {Method} {Path}",
            context.Request.Method, context.Request.Path);

        var problemDetails = MapToProblemDetails(exception, context.TraceIdentifier);

        context.Response.StatusCode = problemDetails.Status ?? 500;
        context.Response.ContentType = "application/problem+json";
        await context.Response.WriteAsJsonAsync(problemDetails);
    });
});
```

## Correlation ID Middleware

```csharp
public class CorrelationIdMiddleware
{
    private const string CorrelationIdHeader = "X-Correlation-ID";
    private readonly RequestDelegate _next;

    public CorrelationIdMiddleware(RequestDelegate next) => _next = next;

    public async Task InvokeAsync(HttpContext context)
    {
        // Read from incoming header or generate new
        if (!context.Request.Headers.TryGetValue(CorrelationIdHeader, out var correlationId)
            || string.IsNullOrWhiteSpace(correlationId))
        {
            correlationId = Guid.NewGuid().ToString();
        }

        // Set on HttpContext for downstream use
        context.TraceIdentifier = correlationId!;

        // Add to response headers
        context.Response.OnStarting(() =>
        {
            context.Response.Headers[CorrelationIdHeader] = correlationId;
            return Task.CompletedTask;
        });

        // Add to log scope for all downstream logging
        using (context.RequestServices.GetRequiredService<ILogger<CorrelationIdMiddleware>>()
            .BeginScope(new Dictionary<string, object> { ["CorrelationId"] = correlationId! }))
        {
            await _next(context);
        }
    }
}

// Extension method for clean registration
public static class CorrelationIdMiddlewareExtensions
{
    public static IApplicationBuilder UseCorrelationId(this IApplicationBuilder builder)
        => builder.UseMiddleware<CorrelationIdMiddleware>();
}
```

## Request / Response Logging Middleware

```csharp
public class RequestLoggingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestLoggingMiddleware> _logger;
    private static readonly HashSet<string> SensitivePaths = new(StringComparer.OrdinalIgnoreCase)
    {
        "/api/auth/login",
        "/api/auth/token"
    };

    public RequestLoggingMiddleware(RequestDelegate next, ILogger<RequestLoggingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var stopwatch = Stopwatch.StartNew();

        try
        {
            await _next(context);
        }
        finally
        {
            stopwatch.Stop();

            if (!SensitivePaths.Contains(context.Request.Path))
            {
                _logger.LogInformation(
                    "HTTP {Method} {Path} responded {StatusCode} in {ElapsedMs}ms",
                    context.Request.Method,
                    context.Request.Path,
                    context.Response.StatusCode,
                    stopwatch.ElapsedMilliseconds);
            }
        }
    }
}
```

## Health Checks

### Readiness vs Liveness

| Check | Purpose | Endpoint | What it Checks |
|-------|---------|----------|----------------|
| **Liveness** | "Is the process running?" | `/health/live` | Nothing (always healthy if responding) |
| **Readiness** | "Can it serve traffic?" | `/health/ready` | Database, Service Bus, external APIs |

### Configuration

```csharp
builder.Services.AddHealthChecks()
    // SQL Server
    .AddSqlServer(
        builder.Configuration.GetConnectionString("BankingDb")!,
        name: "database",
        tags: new[] { "ready" })
    // Azure Service Bus
    .AddAzureServiceBusQueue(
        builder.Configuration["ServiceBus:ConnectionString"]!,
        "payment-events",
        name: "servicebus",
        tags: new[] { "ready" })
    // External API dependency
    .AddUrlGroup(
        new Uri(builder.Configuration["ExternalApi:BaseUrl"]! + "/health"),
        name: "external-api",
        tags: new[] { "ready" });
```

### Custom Health Check

```csharp
public class DatabaseMigrationHealthCheck : IHealthCheck
{
    private readonly IDbConnection _connection;

    public DatabaseMigrationHealthCheck(IDbConnection connection) => _connection = connection;

    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context, CancellationToken ct)
    {
        try
        {
            var version = await _connection.ExecuteScalarAsync<string>(
                "SELECT TOP 1 Version FROM dbo.MigrationHistory ORDER BY AppliedDate DESC");

            return HealthCheckResult.Healthy($"DB migration version: {version}");
        }
        catch (Exception ex)
        {
            return HealthCheckResult.Unhealthy("Database migration check failed", ex);
        }
    }
}
```

## Custom Middleware Pattern

### Class-Based with DI

```csharp
// Middleware that requires scoped services
public class AuditMiddleware
{
    private readonly RequestDelegate _next;

    public AuditMiddleware(RequestDelegate next) => _next = next;

    // Scoped services injected into InvokeAsync, NOT constructor
    public async Task InvokeAsync(HttpContext context, IAuditService auditService)
    {
        await _next(context);

        if (context.Response.StatusCode < 400 && IsMutationRequest(context))
        {
            await auditService.LogRequestAsync(
                context.User.Identity?.Name,
                context.Request.Method,
                context.Request.Path,
                context.Response.StatusCode,
                context.TraceIdentifier);
        }
    }

    private static bool IsMutationRequest(HttpContext context) =>
        context.Request.Method is "POST" or "PUT" or "PATCH" or "DELETE";
}
```

### Unit Testing Middleware

```csharp
[Fact]
public async Task CorrelationId_GeneratesNew_WhenNotInHeader()
{
    // Arrange
    var middleware = new CorrelationIdMiddleware(innerContext =>
    {
        // Assert — inside the pipeline
        Assert.NotNull(innerContext.TraceIdentifier);
        Assert.NotEmpty(innerContext.TraceIdentifier);
        return Task.CompletedTask;
    });

    var context = new DefaultHttpContext();

    // Act
    await middleware.InvokeAsync(context);

    // Assert — response header set
    Assert.True(context.Response.Headers.ContainsKey("X-Correlation-ID"));
}

[Fact]
public async Task CorrelationId_PreservesExisting_WhenInHeader()
{
    var expectedId = "test-correlation-123";
    var middleware = new CorrelationIdMiddleware(innerContext =>
    {
        Assert.Equal(expectedId, innerContext.TraceIdentifier);
        return Task.CompletedTask;
    });

    var context = new DefaultHttpContext();
    context.Request.Headers["X-Correlation-ID"] = expectedId;

    await middleware.InvokeAsync(context);
}
```

## Auth Pipeline Note

Authentication and Authorization middleware ordering is critical:

```csharp
// CORRECT order
app.UseAuthentication();  // First: identify the caller
app.UseAuthorization();   // Then: check permissions

// WRONG: Authorization before Authentication
app.UseAuthorization();   // No identity to check against!
app.UseAuthentication();
```

For full authentication/authorization patterns, consult the team's auth documentation. This skill covers middleware ordering and pipeline concerns only.

## Resilience & Auditability Rules

1. **Correlation IDs are mandatory** — Every request must have a correlation ID generated or propagated. This is non-negotiable for tracing operations across services
2. **Health checks for all dependencies** — Database, Service Bus, external APIs. Use readiness checks (`/health/ready`) for load balancer decisions and liveness checks (`/health/live`) for container orchestration
3. **No internal details in error responses** — Exception middleware must strip stack traces, SQL errors, and internal paths in non-development environments
4. **Rate limiting on mutation endpoints** — Payment and transfer endpoints must be rate-limited to prevent abuse
5. **PII masking in request logs** — Never log request/response bodies for endpoints that handle PII or sensitive data. Log path, method, status code, and duration only

## Review Checklist

### Pipeline Order

- [ ] Exception handler is the first middleware registered?
- [ ] Authentication before Authorization?
- [ ] Routing before Auth middleware?
- [ ] HTTPS redirection and HSTS configured for production?

### Exception Handling

- [ ] Centralized exception handler configured (UseExceptionHandler)?
- [ ] ProblemDetails returned for all errors?
- [ ] Stack traces excluded in non-development environments?
- [ ] Correlation ID included in error responses?

### Observability

- [ ] Correlation ID middleware registered early in pipeline?
- [ ] Correlation ID read from header or generated?
- [ ] Correlation ID propagated to response headers?
- [ ] Request logging captures method, path, status, duration?
- [ ] Sensitive paths excluded from detailed logging?

### Health Checks

- [ ] Readiness endpoint (`/health/ready`) checks all dependencies?
- [ ] Liveness endpoint (`/health/live`) exists (minimal check)?
- [ ] Database health check configured?
- [ ] Service Bus health check configured (if used)?

### Custom Middleware

- [ ] `next()` called exactly once?
- [ ] Scoped services injected via `InvokeAsync` parameters (not constructor)?
- [ ] `context.RequestAborted` respected for long operations?
- [ ] Middleware registered in correct pipeline position?

### Resilience & Auditability

- [ ] Correlation IDs on all requests?
- [ ] Rate limiting on mutation endpoints?
- [ ] PII excluded from request logs?
- [ ] No internal details in production error responses?
