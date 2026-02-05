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

One test class (schema) per database object under test:

```sql
EXEC tSQLt.NewTestClass 'TransferFundsTests';
```

### Naming Convention

Test names must start with `test`. Use natural language with square bracket delimiters:

```sql
-- Pattern: [test <action> <expected behaviour> <when condition>]
CREATE PROCEDURE TransferFundsTests.[test transfer deducts amount from source account]
CREATE PROCEDURE TransferFundsTests.[test transfer fails when insufficient funds]
CREATE PROCEDURE TransferFundsTests.[test transfer is idempotent for duplicate key]
```

### SetUp Procedure

tSQLt executes `SetUp` before every test in that class. Use for shared invariant arrangement only (e.g., `FakeTable` calls). Do NOT put test-specific data in SetUp.

```sql
CREATE PROCEDURE TransferFundsTests.SetUp
AS
BEGIN
    EXEC tSQLt.FakeTable 'Banking.Account';
    EXEC tSQLt.FakeTable 'Banking.Payment';
END;
```

### Transaction Isolation

tSQLt wraps each test in a transaction and rolls it back. Tests cannot leave state behind. Execution order is not guaranteed — tests must be fully independent.

## Core Features

### FakeTable

Replaces a real table with an empty clone stripped of constraints, triggers, identity, defaults, and computed columns.

```sql
EXEC tSQLt.FakeTable 'Banking.Account';                    -- Strips everything
EXEC tSQLt.FakeTable 'Banking.Account', @Identity = 1;     -- Preserve identity (for SCOPE_IDENTITY())
EXEC tSQLt.FakeTable 'Banking.Account', @ComputedColumns = 1;
EXEC tSQLt.FakeTable 'Banking.Account', @Defaults = 1;
```

**Pitfall — `@Identity` omission:** If the procedure uses `SCOPE_IDENTITY()` and you forget `@Identity = 1`, it returns NULL silently.

**Foreign key rule — fake all or none:** If table A has an FK to table B, fake both tables or you get FK violations on insert.

### SpyProcedure

Replaces a stored procedure with a spy that logs calls into `_SpyProcedureLog`:

```sql
EXEC tSQLt.SpyProcedure 'Banking.usp_SendNotification';
EXEC tSQLt.SpyProcedure 'Banking.usp_GetExchangeRate',
    @CommandToExecute = 'SET @Rate = 1.0850';
```

You are NOT testing the spied procedure — you are testing the code that calls it. Verify parameters via `AssertEqualsTable` against the `_SpyProcedureLog`.

### ExpectException

Marks a point after which an exception is expected. Test fails if no exception is raised.

```sql
EXEC tSQLt.ExpectException @ExpectedMessage = 'Transfer amount must be positive';
EXEC Banking.usp_TransferFunds @FromAccount = 1, @ToAccount = 2, @Amount = -100.00;
```

**Placement rule:** Place `ExpectException` immediately before the Act call, not at the top of the test.

### Assertions

| Assertion | Use When |
| --- | --- |
| `AssertEquals` | Scalar value comparisons (counts, IDs, amounts) |
| `AssertEqualsString` | String comparisons |
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

    EXEC Banking.usp_CalculateDailyInterest @AsOfDate = '2024-03-15';

    SELECT AccountId, CAST(Amount AS DECIMAL(18,4)) AS Amount, PostingDate
    INTO #Actual FROM Banking.InterestPosting;

    SELECT TOP(0) * INTO #Expected FROM #Actual;
    INSERT INTO #Expected VALUES (1, 6.8493, '2024-03-15');  -- 100000 * 0.025 / 365

    EXEC tSQLt.AssertEqualsTable '#Expected', '#Actual';
END;
```

## What to Test

### Banking-Specific Priority

1. **Business logic in procs** — Fund transfers, interest calculations, fee assessments, balance computations
2. **Financial calculation precision** — `DECIMAL` assertions with explicit precision, rounding rules
3. **Error paths** — Insufficient funds, invalid accounts, frozen accounts, constraint violations
4. **Idempotency** — Duplicate requests with same idempotency key produce same result, not duplicate effects
5. **Authorization checks** — High-value transfers requiring approval, account status validation

## Common Pitfalls

### Identity Column Loss with FakeTable

**Problem:** FakeTable strips identity by default. If the procedure relies on `SCOPE_IDENTITY()`, it returns NULL.

**Fix:** Use `@Identity = 1` when the code under test needs identity behaviour.

### Transaction Rollback in Production Procs

**Problem:** If the procedure under test contains `ROLLBACK TRANSACTION`, it rolls back tSQLt's wrapping transaction, breaking the test harness.

**Fix:** Use the savepoint pattern in production procedures:

```sql
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
