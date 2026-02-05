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
  |
  +- 1. Exception Handler        <- Catches all downstream exceptions
  +- 2. HSTS                     <- Strict transport security headers
  +- 3. HTTPS Redirection        <- Redirect HTTP to HTTPS
  +- 4. Correlation ID           <- Generate/read correlation ID (custom)
  +- 5. Request Logging          <- Log request summary (custom)
  +- 6. Routing                  <- Match request to endpoint
  +- 7. Rate Limiting            <- Throttle requests
  +- 8. Authentication           <- Identify the caller
  +- 9. Authorization            <- Check permissions
  +- 10. Custom Middleware       <- Business-specific middleware
  +- 11. Endpoints               <- Execute matched endpoint
  |
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
