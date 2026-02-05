---
name: dotnet-testing
description: "Write and run .NET tests following TDD principles. Use when writing tests, implementing TDD workflow, verifying test coverage, or debugging test failures."
---

# .NET Testing Standards

## When to Use This Skill

Use this skill when you need to:

- Write unit tests for new functionality
- Follow TDD (Test-Driven Development) workflow
- Debug failing tests
- Review test quality and coverage
- Understand test naming conventions

## Prerequisites

**Before writing tests:** Read `.planning/CONVENTIONS.md` for repository-specific test patterns (framework, naming, mocking library). If it doesn't exist, the calling agent should invoke the `Repo Analyser` subagent first.

## Hard Rules

### Must

1. **Write failing test first (TDD)** — Test drives the implementation, not vice versa
2. **One assertion concept per test** — Test one behaviour, multiple asserts on same object is OK
3. **Use repo's existing test framework** — Don't mix xUnit and NUnit in same solution
4. **Tests must be deterministic** — No dependency on time, random, or external state
5. **Follow repo's naming convention** — Check CONVENTIONS.md for pattern
6. **Test behaviour, not implementation** — Tests should survive refactoring

### Must Not

1. **Test private methods directly** — Test through public API; if you need to test private, extract a class
2. **Use Thread.Sleep in tests** — Use async/await, polling with timeout, or test doubles
3. **Share mutable state between tests** — Each test gets fresh state
4. **Mock what you don't own** — Wrap third-party APIs, mock the wrapper
5. **Write tests for trivial code** — Auto-properties, simple DTOs don't need tests
6. **Depend on test execution order** — Tests must run independently and in parallel

## TDD Workflow

### Phase 1: RED — Write Failing Test

```
1. Identify the behaviour to implement
2. Write a test that expects that behaviour
3. Run the test — it MUST fail
4. If it passes, either the test is wrong or the feature exists
```

**Command:**

```
dotnet test --filter "FullyQualifiedName~{TestClassName}.{TestMethodName}"
```

### Phase 2: GREEN — Minimal Implementation

```
1. Write the MINIMUM code to make the test pass
2. No extra features, no "nice to haves"
3. Hard-coding is acceptable if it makes the test pass
4. Run the test — it MUST pass
```

### Phase 3: REFACTOR — Clean Up

```
1. Remove duplication
2. Improve naming
3. Extract methods/classes if needed
4. Run ALL tests — they MUST still pass
```

**Command:**

```
dotnet test --no-build --verbosity minimal
```

## Golden Examples

### Test Class Structure (xUnit)

```csharp
public sealed class OrderServiceTests
{
    private readonly Mock<IOrderRepository> _repositoryMock;
    private readonly Mock<IDateTimeProvider> _dateTimeMock;
    private readonly OrderService _sut;

    public OrderServiceTests()
    {
        _repositoryMock = new Mock<IOrderRepository>();
        _dateTimeMock = new Mock<IDateTimeProvider>();
        _sut = new OrderService(_repositoryMock.Object, _dateTimeMock.Object);
    }

    [Fact]
    public async Task GetOrder_WithValidId_ReturnsOrder()
    {
        // Arrange
        var orderId = OrderId.New();
        var expectedOrder = new Order(orderId, "Test Order");
        _repositoryMock
            .Setup(r => r.FindByIdAsync(orderId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedOrder);

        // Act
        var result = await _sut.GetOrderAsync(orderId, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Id.Should().Be(orderId);
    }

    [Fact]
    public async Task GetOrder_WithNonExistentId_ReturnsNotFoundError()
    {
        // Arrange
        var orderId = OrderId.New();
        _repositoryMock
            .Setup(r => r.FindByIdAsync(orderId, It.IsAny<CancellationToken>()))
            .ReturnsAsync((Order?)null);

        // Act
        var result = await _sut.GetOrderAsync(orderId, CancellationToken.None);

        // Assert
        result.IsFailure.Should().BeTrue();
        result.Error.Code.Should().Be("Order.NotFound");
    }
}
```

### Test Naming Patterns

Choose the pattern used in your repo (check CONVENTIONS.md):

```csharp
// Pattern 1: MethodName_Condition_ExpectedResult
public void GetOrder_WithValidId_ReturnsOrder()

// Pattern 2: Should_ExpectedResult_When_Condition
public void Should_ReturnOrder_When_IdIsValid()

// Pattern 3: Given_When_Then
public void GivenValidOrderId_WhenGetOrderCalled_ThenReturnsOrder()
```

### Parameterised Tests (xUnit Theory)

```csharp
[Theory]
[InlineData(0)]
[InlineData(-1)]
[InlineData(-100)]
public void Withdraw_WithInvalidAmount_ThrowsArgumentException(decimal amount)
{
    // Arrange
    var account = new BankAccount(initialBalance: 100m);

    // Act
    var act = () => account.Withdraw(amount);

    // Assert
    act.Should().Throw<ArgumentOutOfRangeException>();
}
```

### Testing Exceptions

```csharp
[Fact]
public async Task ProcessPayment_WhenGatewayFails_ThrowsPaymentException()
{
    // Arrange
    _gatewayMock
        .Setup(g => g.ChargeAsync(It.IsAny<PaymentRequest>(), It.IsAny<CancellationToken>()))
        .ThrowsAsync(new GatewayTimeoutException());

    // Act
    var act = () => _sut.ProcessPaymentAsync(ValidPayment, CancellationToken.None);

    // Assert
    await act.Should().ThrowAsync<PaymentProcessingException>()
        .WithMessage("*gateway*");
}
```

## Anti-Patterns (Don't Do This)

### ❌ Testing Implementation Details

```csharp
// BAD: Verifying internal method calls
_repositoryMock.Verify(r => r.FindByIdAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()), Times.Once);
// This breaks if implementation changes to use caching
```

**Why it's bad:** Tests break when refactoring even if behaviour is unchanged.

### ❌ Testing Multiple Behaviours

```csharp
// BAD: Testing too much in one test
[Fact]
public void OrderService_WorksCorrectly()
{
    // Tests create, update, delete, and query all in one test
}
```

**Why it's bad:** When it fails, you don't know which behaviour broke.

### ❌ Non-Deterministic Tests

```csharp
// BAD: Depends on current time
[Fact]
public void Order_IsExpired_WhenPastExpiryDate()
{
    var order = new Order { ExpiryDate = DateTime.Now.AddDays(-1) };
    order.IsExpired.Should().BeTrue(); // May fail at midnight!
}
```

**Fix:** Inject `IDateTimeProvider` and control time in tests.

### ❌ Over-Mocking

```csharp
// BAD: Mocking the system under test
var sutMock = new Mock<OrderService>();
sutMock.Setup(s => s.Calculate()).Returns(100);
// You're not testing anything real!
```

**Why it's bad:** You're testing your mocks, not your code.

## Test Organisation

```
tests/
├── MyProject.UnitTests/
│   ├── Services/
│   │   └── OrderServiceTests.cs      # Mirrors src structure
│   └── Domain/
│       └── OrderTests.cs
├── MyProject.IntegrationTests/
│   ├── Api/
│   │   └── OrdersEndpointTests.cs
│   └── Fixtures/
│       └── DatabaseFixture.cs
```

## Commands Reference

All `dotnet` commands work identically across all shells.

```
dotnet test
dotnet test ./tests/MyProject.UnitTests/
dotnet test --filter "FullyQualifiedName~OrderServiceTests"
dotnet test --filter "Category=Unit"
dotnet test --filter "FullyQualifiedName!~IntegrationTests & FullyQualifiedName!~Integration.Tests"
dotnet test --list-tests
dotnet test --collect:"XPlat Code Coverage"
```

The compound filter excludes all tests from integration test projects — covering both `IntegrationTests` and `Integration.Tests` naming conventions. Use this when integration tests are excluded via the `quality-gates` skill protocol.

## Verification Checklist

Before considering tests complete:

- [ ] Test fails before implementation (TDD RED)
- [ ] Test passes after implementation (TDD GREEN)
- [ ] Refactoring done with tests still passing
- [ ] Follows naming convention from CONVENTIONS.md
- [ ] One behaviour per test
- [ ] No flaky/non-deterministic elements
- [ ] Mocks are for external dependencies only
- [ ] Test class has same structure as others in repo
