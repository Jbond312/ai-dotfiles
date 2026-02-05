---
name: mssql-stored-procedures
description: "MSSQL stored procedure development standards for banking applications. Use when writing, reviewing, or debugging stored procedures, schema changes, or SQL performance issues. Triggers on: stored procedure, SQL, T-SQL, MSSQL, schema, index, query performance, parameter sniffing, transaction, financial calculation."
---

# MSSQL Stored Procedure Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for repository-specific patterns. Compare changes against these conventions.

## Hard Rules for Review

### Must Flag as Critical

1. **Data integrity risks** — Missing transactions, partial updates without rollback, no `XACT_ABORT`
2. **Financial precision violations** — Using `MONEY`, `FLOAT`, or `REAL` for monetary values instead of `DECIMAL(19,4)`
3. **SQL injection** — String concatenation in dynamic SQL instead of `sp_executesql` with parameters
4. **Missing error handling** — No `TRY/CATCH`, swallowed errors, missing `THROW` in `CATCH` block
5. **Missing `SET XACT_ABORT ON`** — Procedure uses transactions without `XACT_ABORT`, risking orphaned transactions

### Must Flag as Important

1. **SARGability violations** — Functions on columns in `WHERE` clauses preventing index seeks
2. **Cursor usage** — Row-by-row processing where set-based operations are possible
3. **Implicit conversions** — Parameter types not matching column types, causing scans
4. **Missing `SET NOCOUNT ON`** — Unnecessary row count messages sent to client
5. **`NOLOCK` on financial data** — Dirty reads on balance, payment, or transaction tables
6. **Auto-named constraints** — Letting SQL Server generate constraint names

## Stored Procedure Template

The canonical Erland Sommarskog pattern. All stored procedures must follow this structure:

```sql
CREATE OR ALTER PROCEDURE [schema].[usp_ProcedureName]
    @Param1 INT,
    @Param2 DECIMAL(19,4)
AS
SET XACT_ABORT, NOCOUNT ON;

BEGIN TRY
    -- Parameter validation (before starting transaction)
    IF @Param1 IS NULL
        THROW 50001, 'Param1 is required.', 1;

    BEGIN TRANSACTION;

        -- Business logic here

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;  -- Re-raise the original error
END CATCH;
```

**Critical details:**

- `SET XACT_ABORT, NOCOUNT ON` is the ONLY statement before `BEGIN TRY`
- Variable declarations, temp table creation, everything goes inside `BEGIN TRY`
- `THROW` (not `RAISERROR`) re-raises the original error with original severity and state
- Validate parameters BEFORE `BEGIN TRANSACTION` to fail fast without acquiring locks
- Check `@@TRANCOUNT > 0` before `ROLLBACK` to handle nested call scenarios

## Schema Design

### Naming Conventions

| Object Type | Convention | Example |
| --- | --- | --- |
| Tables | PascalCase, singular | `Account`, `Transaction`, `LedgerEntry` |
| Columns | PascalCase | `AccountId`, `TransactionDate`, `BalanceAmount` |
| Stored Procedures | `usp_` prefix | `usp_TransferFunds`, `usp_CalculateInterest` |
| Functions | `fn_` prefix | `fn_GetExchangeRate`, `fn_CalculateInterest` |
| Views | `vw_` prefix | `vw_AccountBalance`, `vw_ActiveAccounts` |
| Clustered Indexes | `PK_` prefix | `PK_Account` |
| Nonclustered Indexes | `IX_` prefix | `IX_Transaction_AccountId_Date` |
| Unique Indexes | `UQ_` prefix | `UQ_Account_AccountNumber` |
| Foreign Keys | `FK_` prefix | `FK_Transaction_Account` |
| Check Constraints | `CK_` prefix | `CK_Transaction_AmountPositive` |
| Default Constraints | `DF_` prefix | `DF_Transaction_CreatedDate` |
| Triggers | `TR_` prefix | `TR_Account_AfterUpdate` |

**Never prefix stored procedures with `sp_`** — SQL Server searches the `master` database first for `sp_` prefixed procedures, adding unnecessary overhead.

### Data Types for Financial Data

```sql
-- BAD: MONEY type loses precision in division/multiplication
CREATE TABLE Banking.Transaction (
    Amount MONEY NOT NULL
);

-- BAD: FLOAT cannot exactly represent decimal values
CREATE TABLE Banking.Transaction (
    Amount FLOAT NOT NULL
);

-- GOOD: Explicit precision and scale
CREATE TABLE Banking.Transaction (
    Amount          DECIMAL(19,4)   NOT NULL,  -- Currency amounts
    ExchangeRate    DECIMAL(15,8)   NULL,      -- Rates need more decimals
    InterestRate    DECIMAL(9,6)    NULL,      -- e.g., 0.045000 = 4.5%
    CurrencyCode    CHAR(3)         NOT NULL,  -- ISO 4217
    CreatedDate     DATETIME2(7)    NOT NULL   -- Not datetime
);
```

| Use Case | Data Type | Notes |
| --- | --- | --- |
| Currency amounts | `DECIMAL(19,4)` | Covers +/-999 trillion with 4 decimal places |
| Exchange rates | `DECIMAL(15,8)` | Needs more decimal precision |
| Interest rates | `DECIMAL(9,6)` | e.g., 0.045000 = 4.5% |
| Dates and times | `DATETIME2(7)` | Not `DATETIME` — higher precision, wider range |
| Identifiers | `BIGINT` | For tables expected to grow |

**Why not `MONEY`?** The `MONEY` type silently truncates beyond 4 decimal places during intermediate calculations. `MONEY / MONEY` produces integer division — a catastrophic financial bug.

### Indexing Strategy

```sql
-- GOOD: Covering index for a common query pattern
CREATE NONCLUSTERED INDEX IX_Transaction_AccountId_Date
ON Banking.Transaction (AccountId, TransactionDate DESC)
INCLUDE (Amount, RunningBalance, TransactionType)
WHERE IsVoided = 0;  -- Filtered index excludes voided transactions

-- BAD: Too-wide index that duplicates storage
CREATE NONCLUSTERED INDEX IX_Transaction_Everything
ON Banking.Transaction (AccountId, TransactionDate, Amount, Description,
    RunningBalance, TransactionType, CreatedBy, ModifiedDate);
```

**Rules:**

- Every table gets a clustered index on a narrow, unique, ever-increasing column (`BIGINT IDENTITY`)
- Follow the ESS principle: **E**quality columns first, then **S**ort columns, then include columns for covering
- Always index foreign key columns — SQL Server does NOT auto-index them
- Use filtered indexes to exclude soft-deleted or voided records
- Consider nonclustered columnstore indexes for analytical/reporting queries on OLTP tables

### Constraints

Always name constraints explicitly. Never let SQL Server auto-generate names.

```sql
-- BAD: Auto-generated name like CK__Transacti__Amoun__4AB81AF0
ALTER TABLE Banking.Transaction
ADD CHECK (Amount > 0);

-- GOOD: Explicit, readable name
ALTER TABLE Banking.Transaction
ADD CONSTRAINT CK_Transaction_AmountPositive CHECK (Amount > 0);

-- GOOD: Foreign key with explicit name and indexed child column
ALTER TABLE Banking.Transaction
ADD CONSTRAINT FK_Transaction_Account
    FOREIGN KEY (AccountId) REFERENCES Banking.Account(AccountId);

CREATE NONCLUSTERED INDEX IX_Transaction_AccountId
ON Banking.Transaction (AccountId);
```

**Banking rule:** Never use `ON DELETE CASCADE` for financial data — audit requirements demand explicit handling.

## Performance

### SARGability

Keep column references clean on one side of the operator. No functions, no arithmetic, no type conversions on the column.

```sql
-- BAD: Function on column forces scan
WHERE YEAR(TransactionDate) = 2024
WHERE ISNULL(Status, 'PENDING') = 'PENDING'
WHERE DATEDIFF(DAY, CreatedDate, GETDATE()) < 30
WHERE CAST(AccountId AS VARCHAR) = '12345'
WHERE Amount * 1.1 > 1000
WHERE LEFT(AccountNumber, 3) = '100'
WHERE LastName LIKE '%Smith'

-- GOOD: Column is clean, index seek possible
WHERE TransactionDate >= '2024-01-01' AND TransactionDate < '2025-01-01'
WHERE (Status = 'PENDING' OR Status IS NULL)
WHERE CreatedDate > DATEADD(DAY, -30, GETDATE())
WHERE AccountId = 12345
WHERE Amount > 1000 - @Fee
WHERE AccountNumber LIKE '100%'
WHERE LastName LIKE 'Smith%'
```

**Common fix patterns:**

| Non-SARGable | SARGable Fix |
| --- | --- |
| `YEAR(col) = 2024` | `col >= '2024-01-01' AND col < '2025-01-01'` |
| `ISNULL(col, 'X') = 'X'` | `(col = 'X' OR col IS NULL)` |
| `DATEDIFF(DAY, col, GETDATE()) < 30` | `col > DATEADD(DAY, -30, GETDATE())` |
| `CONVERT(DATE, col) = '2024-06-15'` | `col >= '2024-06-15' AND col < '2024-06-16'` |

### Parameter Sniffing

SQL Server compiles a stored procedure's execution plan based on the parameter values of the FIRST execution. That plan is cached and reused. If data distribution is highly skewed, the cached plan may be terrible for typical calls.

**Mitigation strategies, ranked by preference:**

```sql
-- Strategy 1: OPTION (RECOMPILE) — best for infrequently called procs
-- or procs where parameters cause wildly different optimal plans
SELECT TransactionId, AccountId, Amount, TransactionDate
FROM Banking.Transaction
WHERE (@AccountId IS NULL OR AccountId = @AccountId)
  AND (@StartDate IS NULL OR TransactionDate >= @StartDate)
OPTION (RECOMPILE);

-- Strategy 2: OPTIMIZE FOR UNKNOWN — uses average statistics
SELECT * FROM Banking.Transaction
WHERE AccountId = @AccountId
OPTION (OPTIMIZE FOR (@AccountId UNKNOWN));

-- Strategy 3: Dynamic SQL with sp_executesql — avoids "kitchen sink" problem
DECLARE @SQL NVARCHAR(MAX) = N'
    SELECT TransactionId, AccountId, Amount
    FROM Banking.Transaction WHERE 1 = 1';
DECLARE @Params NVARCHAR(MAX) = N'
    @AccountId BIGINT, @StartDate DATETIME2';

IF @AccountId IS NOT NULL
    SET @SQL += N' AND AccountId = @AccountId';
IF @StartDate IS NOT NULL
    SET @SQL += N' AND TransactionDate >= @StartDate';

EXEC sp_executesql @SQL, @Params,
    @AccountId = @AccountId, @StartDate = @StartDate;
```

### Set-Based vs Cursors

```sql
-- BAD: Row-by-row interest calculation (cursor)
DECLARE @AccountId BIGINT, @Balance DECIMAL(19,4);
DECLARE account_cursor CURSOR FOR
    SELECT AccountId, Balance FROM Banking.Account WHERE AccountType = 'SAVINGS';

OPEN account_cursor;
FETCH NEXT FROM account_cursor INTO @AccountId, @Balance;

WHILE @@FETCH_STATUS = 0
BEGIN
    UPDATE Banking.Account
    SET Balance = Balance + (Balance * 0.045 / 365)
    WHERE AccountId = @AccountId;

    FETCH NEXT FROM account_cursor INTO @AccountId, @Balance;
END;
CLOSE account_cursor;
DEALLOCATE account_cursor;

-- GOOD: Set-based interest calculation (single pass, 10-100x faster)
UPDATE A
SET A.Balance = A.Balance + (A.Balance * 0.045 / 365),
    A.ModifiedDate = SYSUTCDATETIME()
FROM Banking.Account A
WHERE A.AccountType = 'SAVINGS';
```

**When cursors are acceptable (rare):**

- Calling stored procedures in a loop where each call depends on the previous result
- Sending notifications for each row (external side effects)
- Administrative tasks (rebuilding indexes per table)

### Execution Plan Anti-Patterns

**Key Lookups** — query returns columns not in the nonclustered index:

```sql
-- BAD: Description not in index, causes key lookup per row
SELECT TransactionId, AccountId, Amount, Description
FROM Banking.Transaction
WHERE AccountId = @AccountId;

-- GOOD: Covering index eliminates key lookups
CREATE NONCLUSTERED INDEX IX_Transaction_AccountId
ON Banking.Transaction (AccountId)
INCLUDE (Amount, Description);
```

**Implicit Conversions** — parameter type doesn't match column type:

```sql
-- BAD: If AccountNumber is VARCHAR(20) but @AcctNum is NVARCHAR,
-- SQL Server converts EVERY row's AccountNumber to NVARCHAR (scan!)
DECLARE @AcctNum NVARCHAR(20) = N'1234567890';
SELECT * FROM Banking.Account WHERE AccountNumber = @AcctNum;

-- GOOD: Match types exactly
DECLARE @AcctNum VARCHAR(20) = '1234567890';
SELECT * FROM Banking.Account WHERE AccountNumber = @AcctNum;
```

### Temp Tables vs Table Variables

| Factor | Temp Tables (`#temp`) | Table Variables (`@table`) |
| --- | --- | --- |
| Statistics | Yes (auto-created) | No (optimizer assumes 1 row) |
| Indexes | Full support | Primary key / unique only |
| Parallelism | Full support | Limited |
| Recompilation | Triggers recompile | No recompiles |
| Scope | Session (visible in called procs) | Batch only |

**Rule of thumb:**

- **< ~100 rows, simple usage:** Table variable is fine
- **> 100 rows, or joins/complex filtering:** Use temp table
- **Need nonclustered indexes:** Use temp table

### Isolation Levels for Banking

| Isolation Level | Dirty Reads | Blocking | Banking Use Case |
| --- | --- | --- | --- |
| READ UNCOMMITTED | Yes | None | **Never for financial data** |
| READ COMMITTED (default) | No | Readers block writers | Basic queries |
| READ COMMITTED SNAPSHOT (RCSI) | No | No blocking | **Best default for banking OLTP** |
| SNAPSHOT | No | No blocking | Reports, reconciliation |
| SERIALIZABLE | No | Most locks | **Critical financial transfers** |

**Recommended approach:**

```sql
-- Database level: Enable RCSI as the default
ALTER DATABASE BankingDB SET READ_COMMITTED_SNAPSHOT ON;

-- For critical transfers: escalate to SERIALIZABLE
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

### NOLOCK Risks

`NOLOCK` (`READ UNCOMMITTED`) can cause:

- **Dirty reads** — Reading uncommitted data that later rolls back
- **Phantom reads** — Rows appearing or disappearing mid-query
- **Skipped/duplicate rows** — Due to page splits during scan

**When NOLOCK is acceptable:** Rough row count estimates for monitoring dashboards, truly immutable append-only data.

**When NOLOCK must NEVER be used:** Financial balance calculations, payment processing, regulatory reporting, any query whose results drive business decisions.

## Security

### Dynamic SQL Injection Prevention

```sql
-- BAD: String concatenation — SQL injection vulnerability
DECLARE @SQL NVARCHAR(MAX) = N'
    SELECT * FROM Banking.Account
    WHERE AccountNumber = ''' + @InputAcctNum + N'''';
EXEC(@SQL);

-- GOOD: Parameterised with sp_executesql
DECLARE @SQL NVARCHAR(MAX) = N'
    SELECT * FROM Banking.Account
    WHERE AccountNumber = @AcctNum';
EXEC sp_executesql @SQL,
    N'@AcctNum VARCHAR(20)',
    @AcctNum = @InputAcctNum;

-- GOOD: Dynamic identifiers use QUOTENAME + whitelist validation
IF @TableName NOT IN ('Account', 'Transaction', 'Payment')
    THROW 50100, 'Invalid table name.', 1;

DECLARE @SQL NVARCHAR(MAX) = N'SELECT * FROM ' + QUOTENAME(@TableName);
```

**Rules:**

1. Always use `sp_executesql` with typed parameters for values
2. Use `QUOTENAME()` for any dynamic identifiers (table names, column names)
3. Whitelist-validate dynamic identifiers against a known-good list
4. Never concatenate user input directly into SQL strings

### Principle of Least Privilege

```sql
-- Grant EXECUTE only on specific procedures (never direct table access)
CREATE ROLE BankingAppRole;
GRANT EXECUTE ON Banking.usp_TransferFunds TO BankingAppRole;
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::Banking TO BankingAppRole;
```

Stored procedures act as an API layer. The application user cannot directly manipulate tables.

### Sensitive Data Handling

- Use Always Encrypted for the most sensitive PII (SSN, account numbers)
- Use Dynamic Data Masking for casual protection (names, emails)
- Classify columns containing PII using SQL Server's Data Classification
- Never log sensitive data in error messages or audit tables without masking

## Banking Domain

### Financial Precision

`DECIMAL(19,4)` for all monetary values. Never `MONEY` or `FLOAT`.

```sql
-- BAD: MONEY division bug
DECLARE @m1 MONEY = 1.00, @m2 MONEY = 3.00;
SELECT @m1 / @m2;  -- Returns 0.3333 (truncated incorrectly in chains)

-- GOOD: DECIMAL preserves precision
DECLARE @d1 DECIMAL(19,4) = 1.00, @d2 DECIMAL(19,4) = 3.00;
SELECT @d1 / @d2;  -- Returns 0.333333 (precision maintained per expression rules)
```

### Rounding Rules

Use Banker's rounding (round half to even) for financial calculations. Document rounding rules explicitly in procedure headers.

### Idempotency Pattern

```sql
-- BAD: No idempotency — duplicate requests create duplicate payments
CREATE PROCEDURE Banking.usp_ProcessPayment
    @FromAccountId BIGINT,
    @ToAccountId   BIGINT,
    @Amount        DECIMAL(19,4)
AS
SET XACT_ABORT, NOCOUNT ON;
BEGIN TRY
    BEGIN TRANSACTION;
        UPDATE Banking.Account SET Balance = Balance - @Amount WHERE AccountId = @FromAccountId;
        UPDATE Banking.Account SET Balance = Balance + @Amount WHERE AccountId = @ToAccountId;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

-- GOOD: Idempotency key prevents duplicate processing
CREATE PROCEDURE Banking.usp_ProcessPayment
    @IdempotencyKey UNIQUEIDENTIFIER,
    @FromAccountId  BIGINT,
    @ToAccountId    BIGINT,
    @Amount         DECIMAL(19,4)
AS
SET XACT_ABORT, NOCOUNT ON;
BEGIN TRY
    IF @IdempotencyKey IS NULL
        THROW 50030, 'IdempotencyKey is required.', 1;

    -- Check before transaction to avoid unnecessary lock acquisition
    IF EXISTS (SELECT 1 FROM Banking.Payment WHERE IdempotencyKey = @IdempotencyKey)
        RETURN 0;  -- Already processed

    BEGIN TRANSACTION;
        -- UNIQUE constraint on IdempotencyKey prevents race conditions
        INSERT INTO Banking.Payment (IdempotencyKey, FromAccountId, ToAccountId, Amount, Status)
        VALUES (@IdempotencyKey, @FromAccountId, @ToAccountId, @Amount, 'PROCESSING');

        UPDATE Banking.Account SET Balance = Balance - @Amount
        WHERE AccountId = @FromAccountId AND Balance >= @Amount;
        IF @@ROWCOUNT = 0
            THROW 50031, 'Insufficient funds or account not found.', 1;

        UPDATE Banking.Account SET Balance = Balance + @Amount
        WHERE AccountId = @ToAccountId;

        UPDATE Banking.Payment SET Status = 'COMPLETED'
        WHERE IdempotencyKey = @IdempotencyKey;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
```

### Concurrency Control

**Pessimistic locking** — for critical financial mutations:

```sql
-- CRITICAL: Lock accounts in CONSISTENT ORDER to prevent deadlocks
DECLARE @FirstId BIGINT = IIF(@SourceAccountId < @DestAccountId,
                               @SourceAccountId, @DestAccountId);
DECLARE @SecondId BIGINT = IIF(@SourceAccountId < @DestAccountId,
                                @DestAccountId, @SourceAccountId);

-- Acquire locks in consistent order
SELECT AccountId FROM Banking.Account WITH (UPDLOCK, ROWLOCK)
WHERE AccountId = @FirstId;

SELECT AccountId FROM Banking.Account WITH (UPDLOCK, ROWLOCK)
WHERE AccountId = @SecondId;
```

**Optimistic concurrency** — for low-contention updates:

```sql
-- Using ROWVERSION for optimistic concurrency
UPDATE Banking.CustomerProfile
SET Address = @NewAddress, ModifiedDate = SYSUTCDATETIME()
WHERE CustomerId = @CustomerId AND RowVer = @ExpectedRowVer;

IF @@ROWCOUNT = 0
    THROW 50050, 'Concurrency conflict. Record was modified by another user.', 1;
```

### Audit Trails — Temporal Tables

```sql
-- System-versioned temporal table for automatic audit trail
CREATE TABLE Banking.Account (
    AccountId   BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    Balance     DECIMAL(19,4)   NOT NULL,
    Status      VARCHAR(20)     NOT NULL,

    -- Temporal columns (managed by SQL Server)
    ValidFrom   DATETIME2(7) GENERATED ALWAYS AS ROW START NOT NULL,
    ValidTo     DATETIME2(7) GENERATED ALWAYS AS ROW END NOT NULL,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
)
WITH (SYSTEM_VERSIONING = ON (
    HISTORY_TABLE = Audit.AccountHistory
));

-- Query: What was the balance at a specific point in time?
SELECT AccountId, Balance, ValidFrom, ValidTo
FROM Banking.Account
FOR SYSTEM_TIME AS OF '2024-06-15 14:30:00'
WHERE AccountId = 12345;
```

### Double-Entry Accounting Pattern

Every financial transaction creates at least two entries that sum to zero.

```sql
-- Each line is either a debit or a credit, never both
ALTER TABLE Ledger.JournalLine
ADD CONSTRAINT CK_JournalLine_DebitOrCredit CHECK (
    (DebitAmount > 0 AND CreditAmount = 0) OR
    (DebitAmount = 0 AND CreditAmount > 0)
);

-- Enforce balanced entries with a trigger
CREATE TRIGGER Ledger.TR_JournalEntry_BalanceCheck
ON Ledger.JournalLine
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT JournalEntryId
        FROM Ledger.JournalLine
        WHERE JournalEntryId IN (SELECT DISTINCT JournalEntryId FROM inserted)
        GROUP BY JournalEntryId
        HAVING SUM(DebitAmount) <> SUM(CreditAmount)
    )
        THROW 50060, 'Journal entry is not balanced. Debits must equal credits.', 1;
END;
```

**Key rules:** Journal entries are immutable — corrections are made by posting reversing entries. Balance enforcement belongs at the database level, not just the application.

## Review Checklist

### Schema & Naming

- [ ] Tables use PascalCase singular names?
- [ ] Procedures use `usp_` prefix (not `sp_`)?
- [ ] All constraints are explicitly named?
- [ ] Foreign key columns are indexed?
- [ ] `DATETIME2` used instead of `DATETIME`?
- [ ] `DECIMAL(19,4)` used for monetary values (not `MONEY` or `FLOAT`)?

### Error Handling & Transactions

- [ ] `SET XACT_ABORT, NOCOUNT ON` is the first statement?
- [ ] `TRY/CATCH` wraps all logic?
- [ ] `CATCH` block checks `@@TRANCOUNT > 0` before `ROLLBACK`?
- [ ] `THROW` used to re-raise (not swallowed)?
- [ ] Parameters validated before `BEGIN TRANSACTION`?
- [ ] Transaction scope is minimal (no unnecessary locks held)?

### Performance

- [ ] No functions on columns in `WHERE` clauses (SARGable)?
- [ ] No cursors where set-based operations work?
- [ ] Parameter types match column types (no implicit conversions)?
- [ ] Temp tables used over table variables for > 100 rows?
- [ ] `NOLOCK` not used on financial data?
- [ ] Covering indexes exist for key query patterns?

### Security

- [ ] Dynamic SQL uses `sp_executesql` with parameters?
- [ ] Dynamic identifiers use `QUOTENAME()` and whitelist validation?
- [ ] No sensitive data in error messages or log output?
- [ ] EXECUTE permissions granted instead of direct table access?

### Banking Domain

- [ ] All monetary calculations use `DECIMAL(19,4)`?
- [ ] Operations are idempotent (idempotency key for payments/transfers)?
- [ ] Concurrent access handled (consistent lock ordering or `ROWVERSION`)?
- [ ] Audit trail present (temporal tables or explicit audit records)?
- [ ] Rounding rules documented and explicit?
- [ ] Double-entry accounting entries balance (debits = credits)?
