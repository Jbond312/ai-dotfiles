---
name: tsqlt-testing
description: "tSQLt unit testing standards for SQL Server stored procedures. Use when writing, reviewing, or debugging tSQLt tests, test data patterns, or SQL test isolation. Triggers on: tSQLt, SQL test, unit test SQL, FakeTable, SpyProcedure, test class, stored procedure test."
---

# tSQLt Testing Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for repository-specific patterns. Compare test changes against these conventions.

## Hard Rules for Review

### Must Flag as Critical

1. **Non-deterministic tests** — Tests that depend on `GETDATE()`, `NEWID()`, `RAND()`, or current database state without faking
2. **Missing isolation** — Tests that don't use `FakeTable` for tables read/written by the procedure under test
3. **Multiple behaviours per test** — Tests asserting unrelated outcomes in a single procedure
4. **Swallowed errors** — Using `ExpectNoException` when specific error validation is needed, or missing `ExpectException` for error paths

### Must Flag as Important

1. **Non-descriptive names** — Test names like `test1` or `test transfer works` that don't describe the expected behaviour
2. **Uncontrolled non-determinism** — Not using `FakeFunction` for `GETDATE()` or similar non-deterministic dependencies
3. **Excessive test data** — Inserting dozens of rows when 2-3 would suffice
4. **Missing `@Identity` flag** — FakeTable used without `@Identity = 1` when the procedure relies on `SCOPE_IDENTITY()`
5. **Order-dependent tests** — Tests that pass individually but fail when run as a suite

## Test Structure

### Test Class Organisation

One test class (schema) per database object under test. Create with `tSQLt.NewTestClass`:

```sql
EXEC tSQLt.NewTestClass 'TransferFundsTests';
EXEC tSQLt.NewTestClass 'CalculateInterestTests';
EXEC tSQLt.NewTestClass 'AccountClosureTests';
```

### Naming Convention

Test procedure names must start with `test`. Use natural language with square bracket delimiters:

```sql
-- Pattern: [test <action> <expected behaviour> <when condition>]

-- GOOD: Descriptive, states the expected behaviour
CREATE PROCEDURE TransferFundsTests.[test transfer deducts amount from source account]
CREATE PROCEDURE TransferFundsTests.[test transfer fails when insufficient funds]
CREATE PROCEDURE TransferFundsTests.[test transfer rejects negative amount]
CREATE PROCEDURE TransferFundsTests.[test transfer is idempotent for duplicate key]

-- BAD: Vague, doesn't state expectation
CREATE PROCEDURE TransferFundsTests.[test1]
CREATE PROCEDURE TransferFundsTests.[test transfer works]
CREATE PROCEDURE TransferFundsTests.[test happy path]
```

### SetUp Procedure

If a `SetUp` procedure exists in a test class schema, tSQLt executes it before every test in that class:

```sql
CREATE PROCEDURE TransferFundsTests.SetUp
AS
BEGIN
    -- Fake tables used by all tests in this class
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.FakeTable 'Banking.Payment';
    EXEC tSQLt.FakeTable 'Banking.Transaction';
END;
```

**Rules:**

- Use SetUp for shared, invariant arrangement (`FakeTable` calls, baseline reference data)
- Do NOT put test-specific data in SetUp — that belongs in the individual test's Arrange section
- Keep SetUp minimal — if different tests need different configurations, use per-test arrangement

### Transaction Isolation

tSQLt automatically wraps each test in a transaction and rolls it back:

1. tSQLt starts a transaction
2. `SetUp` runs (if it exists)
3. Test procedure runs
4. Transaction is rolled back (regardless of pass/fail)

Tests cannot leave state behind. Execution order within a class is not guaranteed — tests must be fully independent.

## Core Features & Patterns

### FakeTable

Replaces a real table with an empty clone that has no constraints, no triggers, no identity, no defaults, and no computed columns — unless you opt in.

```sql
-- Basic: strips everything
EXEC tSQLt.FakeTable 'Banking.Account';

-- Preserve identity (needed when proc uses SCOPE_IDENTITY())
EXEC tSQLt.FakeTable 'Banking.Account', @Identity = 1;

-- Preserve computed columns
EXEC tSQLt.FakeTable 'Banking.Account', @ComputedColumns = 1;

-- Preserve defaults
EXEC tSQLt.FakeTable 'Banking.Account', @Defaults = 1;
```

**Foreign key rule — fake all or none:**

```sql
-- BAD: FK violation because Currencies table is real
EXEC tSQLt.FakeTable 'Banking.Account';
INSERT INTO Banking.Account (AccountId, CurrencyCode) VALUES (1, 'USD');  -- FK error!

-- GOOD: Fake both tables in the relationship
EXEC tSQLt.FakeTable 'Banking.Account';
EXEC tSQLt.FakeTable 'Banking.Currency';
INSERT INTO Banking.Currency (CurrencyCode) VALUES ('USD');
INSERT INTO Banking.Account (AccountId, CurrencyCode) VALUES (1, 'USD');
```

### SpyProcedure

Replaces a stored procedure with a "spy" that logs calls and parameters into a `_SpyProcedureLog` table:

```sql
-- Basic spy: records calls
EXEC tSQLt.SpyProcedure 'Banking.usp_SendNotification';

-- Spy with replacement behaviour
EXEC tSQLt.SpyProcedure 'Banking.usp_GetExchangeRate',
    @CommandToExecute = 'SET @Rate = 1.0850';
```

**Verifying parameters:**

```sql
CREATE PROCEDURE TransferFundsTests.[test transfer calls audit logging with correct parameters]
AS
BEGIN
    EXEC tSQLt.SpyProcedure 'Banking.usp_LogAuditEvent';

    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    -- Act
    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;

    -- Assert: verify the audit procedure was called with expected parameters
    SELECT FromAccount, ToAccount, Amount
    INTO #Actual
    FROM Banking.usp_LogAuditEvent_SpyProcedureLog;

    SELECT TOP(0) * INTO #Expected FROM #Actual;
    INSERT INTO #Expected VALUES (1, 2, 1000.00);

    EXEC tSQLt.AssertEqualsTable '#Expected', '#Actual';
END;
```

**Key understanding:** Spying replaces the procedure. You are NOT testing the spied procedure — you are testing the code that calls it.

### ExpectException

Marks a point after which an exception is expected. If no exception is raised, the test fails.

```sql
CREATE PROCEDURE TransferFundsTests.[test transfer fails with negative amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    EXEC tSQLt.ExpectException @ExpectedMessage = 'Transfer amount must be positive';

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = -100.00;
END;

-- Can also match by error number, pattern, severity, or state
EXEC tSQLt.ExpectException
    @ExpectedMessagePattern = '%insufficient%funds%',
    @ExpectedSeverity = 16;
```

**Placement rule:** Place `ExpectException` immediately before the Act (the call that should throw), not at the top of the test.

### ExpectNoException

Marks a point after which NO error should occur. Converts unexpected errors from ERROR to FAIL status.

```sql
CREATE PROCEDURE TransferFundsTests.[test transfer succeeds with exact balance amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 500.00), (2, 0.00);

    EXEC tSQLt.ExpectNoException;

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 500.00;
END;
```

### Assertions

| Assertion | Use When |
| --- | --- |
| `AssertEquals` | Scalar value comparisons (counts, IDs, amounts) |
| `AssertEqualsString` | String comparisons (names, codes) |
| `AssertEqualsTable` | Result set validation — **the workhorse for financial testing** |
| `AssertEqualsTableSchema` | DDL testing, migration validation |
| `AssertObjectExists` | Verifying database objects exist |
| `AssertEmptyTable` | Testing delete/purge operations |
| `AssertLike` | Partial string matching |
| `Fail` | Guard clauses, manual assertion logic |

**AssertEqualsTable pattern (most important for banking):**

```sql
CREATE PROCEDURE InterestTests.[test daily interest calculation for savings account]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.FakeTable 'Banking.InterestPosting';

    INSERT INTO Banking.Account (AccountId, Balance, InterestRate, AccountType)
    VALUES (1, 100000.0000, 0.0250, 'SAVINGS');

    -- Act
    EXEC Banking.usp_CalculateDailyInterest @AsOfDate = '2024-03-15';

    -- Assert
    SELECT AccountId, CAST(Amount AS DECIMAL(18,4)) AS Amount, PostingDate
    INTO #Actual
    FROM Banking.InterestPosting;

    SELECT TOP(0) * INTO #Expected FROM #Actual;
    INSERT INTO #Expected VALUES (1, 6.8493, '2024-03-15');  -- 100000 * 0.025 / 365

    EXEC tSQLt.AssertEqualsTable '#Expected', '#Actual';
END;
```

**NULL handling note:** In tSQLt, `AssertEquals NULL, NULL` passes. This differs from standard SQL three-valued logic and is intentional.

### FakeFunction

Replaces a scalar or table-valued function with a fake. Both must be the same type with matching parameters.

```sql
-- Create a fake that returns a hard-coded date
CREATE FUNCTION TestHelpers.Fake_GetCurrentDate()
RETURNS DATE AS BEGIN RETURN '2024-06-15'; END;

-- In the test:
EXEC tSQLt.FakeFunction 'dbo.fn_GetCurrentDate', 'TestHelpers.Fake_GetCurrentDate';
-- Now all code calling fn_GetCurrentDate gets 2024-06-15
```

### ApplyConstraint and ApplyTrigger

After `FakeTable` removes everything, selectively re-apply a single constraint or trigger for isolated testing:

```sql
-- Test a single constraint in isolation
CREATE PROCEDURE AccountTests.[test balance cannot be negative]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.ApplyConstraint 'Banking.Account', 'CK_Account_NonNegativeBalance';

    EXEC tSQLt.ExpectException;

    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, -100.00);
END;

-- Test a single trigger in isolation
CREATE PROCEDURE AuditTests.[test insert trigger writes audit record]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.FakeTable 'Banking.AuditLog';
    EXEC tSQLt.ApplyTrigger 'Banking.Account', 'TR_Account_AuditInsert';

    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00);

    DECLARE @AuditCount INT;
    SELECT @AuditCount = COUNT(*) FROM Banking.AuditLog;
    EXEC tSQLt.AssertEquals 1, @AuditCount;
END;
```

## What to Test

### Banking-Specific Priority

1. **Business logic in procs** — Fund transfers, interest calculations, fee assessments, balance computations
2. **Financial calculation precision** — `DECIMAL` assertions with explicit precision, rounding rules
3. **Error paths** — Insufficient funds, invalid accounts, frozen accounts, constraint violations
4. **Idempotency** — Duplicate requests with same idempotency key produce same result, not duplicate effects
5. **Authorization checks** — High-value transfers requiring approval, account status validation

### Error Path Testing

```sql
CREATE PROCEDURE TransferFundsTests.[test transfer fails with insufficient funds]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 50.00), (2, 0.00);

    EXEC tSQLt.ExpectException @ExpectedMessagePattern = '%insufficient%funds%';

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;
END;

CREATE PROCEDURE TransferFundsTests.[test transfer rejects NULL amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 0.00);

    EXEC tSQLt.ExpectException @ExpectedMessagePattern = '%amount%';

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = NULL;
END;
```

### Boundary Value Testing

```sql
CREATE PROCEDURE TransferFundsTests.[test transfer allows exact balance amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 500.00), (2, 0.00);

    EXEC tSQLt.ExpectNoException;

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 500.00;
END;

CREATE PROCEDURE TransferFundsTests.[test transfer rejects zero amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 500.00), (2, 0.00);

    EXEC tSQLt.ExpectException;

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 0.00;
END;
```

## What NOT to Test

1. **SQL Server engine internals** — Don't test that joins, aggregations, or transactions work. Trust the engine.
2. **Framework-provided behaviour** — Don't test that tSQLt's `FakeTable` works or that transactions roll back.
3. **Implementation details** — Test what a procedure produces, not how it achieves it. Refactoring internals should not break tests.
4. **Exact column order in views** — Test the data a view returns, not its column ordering.
5. **Frequently-changing reference data** — Use `FakeTable` to control reference data instead of hardcoding current values.

```sql
-- BAD: Tests SQL Server, not your code
CREATE PROCEDURE BadTests.[test left join returns nulls for non-matching rows]
AS ...

-- BAD: Brittle, breaks if columns reordered
CREATE PROCEDURE BadTests.[test account view column order]
AS
BEGIN
    EXEC tSQLt.AssertResultSetsHaveSameMetaData
        'SELECT AccountId, Name, Balance FROM expected',
        'SELECT * FROM Banking.vw_Accounts';
END;

-- GOOD: Tests behaviour — does the view return correct data?
CREATE PROCEDURE ViewTests.[test active accounts view excludes closed accounts]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    INSERT INTO Banking.Account (AccountId, Status) VALUES (1, 'Active'), (2, 'Closed');

    SELECT AccountId INTO #Actual FROM Banking.vw_ActiveAccounts;

    SELECT TOP(0) * INTO #Expected FROM #Actual;
    INSERT INTO #Expected VALUES (1);

    EXEC tSQLt.AssertEqualsTable '#Expected', '#Actual';
END;
```

## Test Data Patterns

### Minimal Test Data

Insert only the data your specific test needs. Fewer rows = faster tests, easier debugging, clearer intent.

```sql
-- BAD: 100 accounts for a test that only needs 2
-- GOOD: Only the accounts involved
CREATE PROCEDURE TransferFundsTests.[test transfer moves exact amount]
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00);
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (2, 3000.00);

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;

    DECLARE @SourceBalance DECIMAL(18,4);
    SELECT @SourceBalance = Balance FROM Banking.Account WHERE AccountId = 1;
    EXEC tSQLt.AssertEquals 4000.00, @SourceBalance;
END;
```

### Test Data Factory Helpers

Create reusable helpers in a shared schema to reduce repetition:

```sql
EXEC tSQLt.NewTestClass 'TestHelpers';

CREATE PROCEDURE TestHelpers.CreateAccount
    @AccountId INT = 1,
    @Balance DECIMAL(19,4) = 1000.00,
    @Currency CHAR(3) = 'USD',
    @Status VARCHAR(20) = 'Active',
    @AccountType VARCHAR(20) = 'CHECKING'
AS
BEGIN
    INSERT INTO Banking.Account (AccountId, Balance, CurrencyCode, Status, AccountType)
    VALUES (@AccountId, @Balance, @Currency, @Status, @AccountType);
END;

-- Usage: defaults make tests readable — only override what matters
CREATE PROCEDURE TransferFundsTests.[test transfer between USD accounts]
AS
BEGIN
    EXEC TestHelpers.CreateAccount @AccountId = 1, @Balance = 5000.00;
    EXEC TestHelpers.CreateAccount @AccountId = 2, @Balance = 3000.00;

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;
    -- Assert...
END;
```

### Deterministic Data

Never rely on `GETDATE()`, `NEWID()`, or `RAND()` in test data or assertions. Use `FakeFunction` to control non-determinism.

### Identity Column Handling

```sql
-- Default FakeTable: identity stripped, explicit IDs work (usually desirable)
EXEC tSQLt.FakeTable 'Banking.Account';
INSERT INTO Banking.Account (AccountId, Balance) VALUES (42, 5000.00);  -- Works!

-- Preserve identity when proc uses SCOPE_IDENTITY()
EXEC tSQLt.FakeTable 'Banking.Account', @Identity = 1;
INSERT INTO Banking.Account (Balance) VALUES (5000.00);  -- AccountId auto-assigned
```

## Common Pitfalls

### Identity Column Loss with FakeTable

**Problem:** FakeTable strips identity by default. If the procedure relies on `SCOPE_IDENTITY()`, it returns NULL.

**Fix:** Use `@Identity = 1` when the code under test needs identity behaviour.

### Transaction Rollback in Production Procs

**Problem:** If the procedure under test contains `ROLLBACK TRANSACTION`, it rolls back tSQLt's wrapping transaction, breaking the test harness.

**Fix:** Use the savepoint pattern in production procedures:

```sql
-- Production proc compatible with tSQLt
CREATE PROCEDURE Banking.usp_DebitAccount
    @AccountId BIGINT,
    @Amount    DECIMAL(19,4)
AS
SET XACT_ABORT, NOCOUNT ON;
BEGIN TRY
    DECLARE @TransactionStarted BIT = 0;

    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @TransactionStarted = 1;
    END;

    UPDATE Banking.Account SET Balance = Balance - @Amount WHERE AccountId = @AccountId;

    IF @TransactionStarted = 1
        COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 AND @TransactionStarted = 1
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
```

### Schema-Bound Dependencies

**Problem:** Tables referenced by views with `SCHEMABINDING` cannot be faked.

**Workaround:** Use `tSQLt.SetFakeViewOn` / `tSQLt.SetFakeViewOff` before faking the underlying tables.

### Temp Table Testing

**Problem:** `FakeTable` cannot fake temp tables (`#` or `##` prefixes).

**Workaround:** Fake the persistent tables the procedure reads from, execute the procedure, and assert on the persistent tables it writes to. Test the output, not the internal temp tables.

```sql
CREATE PROCEDURE ReportTests.[test monthly statement aggregates correctly]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Transaction';

    INSERT INTO Banking.Transaction (AccountId, Amount, TxnDate, TxnType) VALUES
        (1, 1000.00, '2024-06-01', 'Credit'),
        (1, -200.00, '2024-06-05', 'Debit');

    -- Procedure internally uses temp tables, but we test its output
    CREATE TABLE #Actual (AccountId INT, TotalCredits DECIMAL(18,4), TotalDebits DECIMAL(18,4));
    INSERT INTO #Actual EXEC Banking.usp_GetMonthlyStatement @AccountId = 1, @Month = '2024-06';

    CREATE TABLE #Expected (AccountId INT, TotalCredits DECIMAL(18,4), TotalDebits DECIMAL(18,4));
    INSERT INTO #Expected VALUES (1, 1000.00, 200.00);

    EXEC tSQLt.AssertEqualsTable '#Expected', '#Actual';
END;
```

### Dynamic SQL Testing

Dynamic SQL in procedures cannot be directly intercepted by tSQLt. Fake the tables, execute the procedure, and assert on results — treat it as an integration-level test.

### Cross-Database Testing

tSQLt is database-scoped. `FakeTable` and `SpyProcedure` only work on objects in the database where tSQLt is installed. For cross-database references, use synonyms to redirect to local test doubles.

### Temporal Table Testing

**Problem:** System-versioned temporal tables have constraints that make them difficult to fake.

**Workaround:** Use `FakeTable` on the temporal table — this replaces it with a regular table, avoiding temporal constraints entirely. Alternatively, disable system versioning at the start of the test.

### Concurrency Limitations

tSQLt is single-session and single-threaded. It cannot test true concurrency scenarios (deadlocks, race conditions). Use external tools (SQLQueryStress, ostress) for concurrency testing.

## Good vs Bad Examples

### Test Isolation

```sql
-- BAD: No FakeTable, test depends on real database state
CREATE PROCEDURE TransferFundsTests.[test transfer moves amount]
AS
BEGIN
    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 100.00;
    -- Depends on whatever is in the real Account table!
END;

-- GOOD: Full isolation with FakeTable
CREATE PROCEDURE TransferFundsTests.[test transfer moves amount]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.FakeTable 'Banking.Transaction';

    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;

    DECLARE @SourceBalance DECIMAL(18,4);
    SELECT @SourceBalance = Balance FROM Banking.Account WHERE AccountId = 1;
    EXEC tSQLt.AssertEquals 4000.00, @SourceBalance;
END;
```

### Assertions

```sql
-- BAD: No assertion at all — test passes as long as nothing throws
CREATE PROCEDURE TransferFundsTests.[test transfer works]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;
    -- No assertion! Passes even if the transfer did nothing.
END;

-- GOOD: Specific, targeted assertion
CREATE PROCEDURE TransferFundsTests.[test transfer credits destination account]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;

    DECLARE @DestBalance DECIMAL(18,4);
    SELECT @DestBalance = Balance FROM Banking.Account WHERE AccountId = 2;
    EXEC tSQLt.AssertEquals 4000.00, @DestBalance;
END;
```

### Test Data

```sql
-- BAD: Massive test data setup obscuring the test intent
CREATE PROCEDURE TransferFundsTests.[test transfer with too much data]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    INSERT INTO Banking.Account VALUES (1, 5000, 'USD', 'Active', 'CHECKING', 1, '2024-01-01', NULL);
    INSERT INTO Banking.Account VALUES (2, 3000, 'USD', 'Active', 'SAVINGS', 1, '2024-01-01', NULL);
    INSERT INTO Banking.Account VALUES (3, 8000, 'EUR', 'Active', 'CHECKING', 2, '2024-02-01', NULL);
    INSERT INTO Banking.Account VALUES (4, 1000, 'GBP', 'Closed', 'SAVINGS', 3, '2024-03-01', NULL);
    -- ... 20 more rows that have nothing to do with this test
END;

-- GOOD: Minimal data, only what the test needs
CREATE PROCEDURE TransferFundsTests.[test transfer between accounts]
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    INSERT INTO Banking.Account (AccountId, Balance) VALUES (1, 5000.00), (2, 3000.00);

    EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = 1000.00;
    -- Assert...
END;
```

## Review Checklist

### Structure & Naming

- [ ] One test class per database object under test?
- [ ] Test names follow `[test <action> <expected> <when>]` pattern?
- [ ] Test names describe the expected behaviour, not implementation?
- [ ] `SetUp` procedure contains only shared invariant arrangement?

### Isolation

- [ ] `FakeTable` used for all tables the procedure reads from or writes to?
- [ ] All tables in foreign key chains are faked together?
- [ ] `SpyProcedure` used for external dependencies called by the procedure under test?
- [ ] `FakeFunction` used for non-deterministic functions (`GETDATE`, `NEWID`)?
- [ ] `@Identity = 1` used when the procedure relies on `SCOPE_IDENTITY()`?

### Assertions

- [ ] Every test has at least one assertion (not just "doesn't throw")?
- [ ] Assertions are specific to the behaviour being tested?
- [ ] `AssertEqualsTable` used for result set validation?
- [ ] `ExpectException` used with specific message/pattern/number (not just "any exception")?
- [ ] Financial assertions use explicit `DECIMAL` precision?

### Test Data

- [ ] Minimal rows — only what the test needs?
- [ ] Test data factory helpers used for common patterns?
- [ ] No reliance on `GETDATE()`, `NEWID()`, or current database state?
- [ ] Explicit, readable values (not auto-generated)?

### Pitfall Avoidance

- [ ] Production procs use savepoint pattern (compatible with tSQLt's wrapping transaction)?
- [ ] No temp table faking attempted (test output instead)?
- [ ] Schema-bound views handled with `SetFakeViewOn`/`SetFakeViewOff`?
- [ ] Tests pass when run individually AND as part of the full suite?
