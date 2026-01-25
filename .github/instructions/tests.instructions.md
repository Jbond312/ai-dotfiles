---
applyTo: "**/*.Tests/**/*.cs,**/*.Tests.Integration/**/*.cs,**/tests/**/*.cs"
description: "Testing conventions for test files"
---

# Testing Conventions

Integration tests first (honeycomb model). A feature is not complete without passing tests.

## When to Unit Test

Complex algorithms, pure functions, domain invariants.

## Test Naming

Describe behaviour: `Should_return_declined_result_when_balance_insufficient`

Or class-per-scenario: class `WhenProcessingPaymentWithInsufficientFunds`, method `Should_return_declined_result`.

Match existing conventions in the test project.

## Structure

```csharp
// Arrange
var account = await CreateAccountWithBalance(0m);

// Act
var result = await Sut.ProcessAsync(payment);

// Assert
result.Should().BeOfType<DeclinedResult>();
```

## Assertions

Be specific. Assert on observable outcomes, not implementation details. Use FluentAssertions.

## External Services

Use WireMock for external APIs. Don't call real third-party services.

## Determinism

No flaky tests. Control time, isolate state, clean up after.

Refer to `dotnet-testing` skill for execution patterns.
