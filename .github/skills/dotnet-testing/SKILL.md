---
name: dotnet-testing
description: "Run and verify .NET tests, check test baseline, execute specific tests. Use when running tests, verifying test coverage, checking if tests pass, or debugging test failures. Triggers on: run tests, dotnet test, test baseline, verify tests, test discovery, failing tests, TDD."
---

# .NET Testing

## Verify Test Baseline

**Before making changes**, confirm existing tests pass:

```bash
# Find test projects
find . -name "*.Tests.csproj" -o -name "*.Tests.*.csproj" | head -5

# Run all tests
dotnet test --no-build --verbosity minimal
```

**Critical:** Verify tests were discovered. Output must show test counts:

```
Passed!  - Failed: 0, Passed: 42, Skipped: 0, Total: 42
```

If `Total tests: 0`, you're in the wrong directory or targeting wrong project. Find the test project explicitly and run from there.

## Running Specific Tests

```bash
# Single test by name
dotnet test --filter "FullyQualifiedName~YourTestName"

# Tests in a namespace
dotnet test --filter "FullyQualifiedName~Payments.Tests"

# Run specific test project
dotnet test path/to/Tests.csproj
```

## Test Project Locations

Common patterns:

- `*.Tests/` — Unit tests
- `*.Tests.Integration/` — Integration tests
- `tests/` or `test/` — All tests in dedicated folder

## Integration Test Structure

```csharp
public class WhenProcessingPaymentWithInsufficientFunds : IntegrationTestBase
{
    [Fact]
    public async Task Should_return_declined_result()
    {
        // Arrange
        var account = await CreateAccountWithBalance(0m);
        var payment = new PaymentRequest(account.Id, Amount: 100m);

        // Act
        var result = await Sut.ProcessAsync(payment);

        // Assert
        result.Should().BeOfType<DeclinedResult>();
        result.As<DeclinedResult>().Reason.Should().Be(DeclineReason.InsufficientFunds);
    }
}
```

## Confirm Test Failure (TDD)

When writing test-first, verify the test fails before implementing:

```bash
dotnet test --filter "FullyQualifiedName~YourNewTest"
```

Test should fail because production code doesn't exist yet. If it passes, behaviour may already exist or test isn't testing what you think.

## Troubleshooting

| Problem              | Cause                   | Solution                                     |
| -------------------- | ----------------------- | -------------------------------------------- |
| `Total tests: 0`     | Wrong directory/project | Find test project, run explicitly            |
| Tests not discovered | Missing test SDK        | Check `.csproj` has `Microsoft.NET.Test.Sdk` |
| Timeout              | Slow integration tests  | Check database/service availability          |
