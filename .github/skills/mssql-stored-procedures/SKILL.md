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

1. **SARGability violations** — Functions on columns in `WHERE` clauses preventing index seeks (e.g., `YEAR(col) = 2024` instead of range predicates)
2. **Cursor usage** — Row-by-row processing where set-based operations are possible
3. **Implicit conversions** — Parameter types not matching column types, causing scans
4. **Missing `SET NOCOUNT ON`** — Unnecessary row count messages sent to client
5. **`NOLOCK` on financial data** — Dirty reads on balance, payment, or transaction tables. `NOLOCK` must NEVER be used on financial balance calculations, payment processing, or regulatory reporting
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
