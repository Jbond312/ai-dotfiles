---
name: dapper-data-access
description: "Dapper data access patterns for .NET applications. Use when writing, reviewing, or debugging Dapper queries, repository methods, connection management, or stored procedure calls from C#. Triggers on: Dapper, IDbConnection, SqlConnection, QueryAsync, ExecuteAsync, DynamicParameters, data access, repository."
---

# Dapper Data Access Standards

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's data access patterns (raw Dapper, Dapper.Contrib, DapperAOT). Follow the established approach.

## Hard Rules for Review

### Must Flag as Critical

1. **SQL injection** — String concatenation or interpolation in SQL queries instead of parameterised queries
2. **Undisposed connections** — `IDbConnection` created without `using` statement or `IAsyncDisposable` pattern
3. **Wrong CommandType** — Calling stored procedures with `CommandType.Text` instead of `CommandType.StoredProcedure`
4. **Missing transactions** — Multi-statement writes without transaction wrapping
5. **Type mismatches** — C# parameter types not matching SQL column types (causes implicit conversions and scans)

### Must Flag as Important

1. **Missing CancellationToken** — Async queries without `CancellationToken` propagation via `CommandDefinition`
2. **SELECT \*** — Querying all columns when only a subset is needed
3. **N+1 queries** — Loading related data in a loop instead of using `QueryMultiple` or joins
4. **Missing async** — Using `Query` when `QueryAsync` is available
5. **Hardcoded connection strings** — Connection strings outside of configuration/DI

## Connection Management

### DI Factory Pattern

```csharp
// Registration — inject a factory, not a connection
builder.Services.AddTransient<IDbConnection>(sp =>
    new SqlConnection(sp.GetRequiredService<IConfiguration>()
        .GetConnectionString("BankingDb")));

// Usage — always use 'using' for disposal
public class AccountRepository
{
    private readonly IDbConnection _connection;

    public AccountRepository(IDbConnection connection) => _connection = connection;

    public async Task<Account?> GetByIdAsync(long accountId, CancellationToken ct)
    {
        var command = new CommandDefinition(
            "SELECT AccountId, Balance, Status FROM Banking.Account WHERE AccountId = @AccountId",
            new { AccountId = accountId },
            cancellationToken: ct);

        return await _connection.QuerySingleOrDefaultAsync<Account>(command);
    }
}
```

### Connection Pooling

SQL Server connection pooling is automatic via `SqlConnection`. Do NOT cache or reuse connection instances — create, use, dispose. The pool handles reuse transparently.

```csharp
// BAD: Holding connection open across requests
private readonly SqlConnection _connection; // Singleton or Scoped — pool starvation risk

// GOOD: Transient connection from DI — disposed per use
public async Task<Account?> GetByIdAsync(long id, CancellationToken ct)
{
    using var connection = new SqlConnection(_connectionString);
    // Connection opens lazily on first query, disposes back to pool
    return await connection.QuerySingleOrDefaultAsync<Account>(sql, new { Id = id });
}
```

## Querying Patterns

### Basic Query

```csharp
// Single row
var account = await connection.QuerySingleOrDefaultAsync<Account>(
    "SELECT AccountId, Balance, Status FROM Banking.Account WHERE AccountId = @Id",
    new { Id = accountId });

// Multiple rows
var transactions = await connection.QueryAsync<Transaction>(
    "SELECT TransactionId, Amount, TransactionDate FROM Banking.Transaction " +
    "WHERE AccountId = @AccountId AND TransactionDate >= @Since ORDER BY TransactionDate DESC",
    new { AccountId = accountId, Since = startDate });
```

### Multi-Mapping (Joins)

```csharp
var sql = """
    SELECT a.AccountId, a.Balance, a.Status,
           c.CustomerId, c.FullName, c.Email
    FROM Banking.Account a
    INNER JOIN Banking.Customer c ON a.CustomerId = c.CustomerId
    WHERE a.AccountId = @AccountId
    """;

var account = await connection.QueryAsync<Account, Customer, Account>(
    sql,
    (account, customer) =>
    {
        account.Customer = customer;
        return account;
    },
    new { AccountId = accountId },
    splitOn: "CustomerId");
```

### QueryMultiple (Multiple Result Sets)

```csharp
// BAD: N+1 — separate query for each related entity
var account = await connection.QuerySingleAsync<Account>(accountSql, new { Id = id });
var transactions = await connection.QueryAsync<Transaction>(txnSql, new { AccountId = id });
var alerts = await connection.QueryAsync<Alert>(alertSql, new { AccountId = id });

// GOOD: Single round trip with multiple result sets
var sql = """
    SELECT AccountId, Balance, Status FROM Banking.Account WHERE AccountId = @Id;
    SELECT TransactionId, Amount, TransactionDate FROM Banking.Transaction WHERE AccountId = @Id ORDER BY TransactionDate DESC;
    SELECT AlertId, Message, CreatedDate FROM Banking.Alert WHERE AccountId = @Id AND IsRead = 0;
    """;

using var multi = await connection.QueryMultipleAsync(sql, new { Id = accountId });
var account = await multi.ReadSingleOrDefaultAsync<Account>();
var transactions = (await multi.ReadAsync<Transaction>()).ToList();
var alerts = (await multi.ReadAsync<Alert>()).ToList();
```

### IN Clause

```csharp
// Dapper expands IEnumerable parameters for IN clauses automatically
var accounts = await connection.QueryAsync<Account>(
    "SELECT AccountId, Balance FROM Banking.Account WHERE AccountId IN @Ids",
    new { Ids = accountIds });
```

## Stored Procedure Calling

Cross-reference `mssql-stored-procedures` skill for the stored procedure implementation patterns.

### Basic Call

```csharp
var result = await connection.QuerySingleOrDefaultAsync<TransferResult>(
    "Banking.usp_TransferFunds",
    new { FromAccountId = source, ToAccountId = dest, Amount = amount, IdempotencyKey = key },
    commandType: CommandType.StoredProcedure);
```

### DynamicParameters with OUTPUT

```csharp
var parameters = new DynamicParameters();
parameters.Add("@AccountId", accountId);
parameters.Add("@Amount", amount);
parameters.Add("@NewBalance", dbType: DbType.Decimal, direction: ParameterDirection.Output, precision: 19, scale: 4);
parameters.Add("@ReturnValue", dbType: DbType.Int32, direction: ParameterDirection.ReturnValue);

await connection.ExecuteAsync(
    "Banking.usp_DebitAccount",
    parameters,
    commandType: CommandType.StoredProcedure);

var newBalance = parameters.Get<decimal>("@NewBalance");
var returnCode = parameters.Get<int>("@ReturnValue");
```

### Multiple Result Sets from Stored Procedure

```csharp
using var multi = await connection.QueryMultipleAsync(
    "Banking.usp_GetAccountSummary",
    new { AccountId = accountId },
    commandType: CommandType.StoredProcedure);

var account = await multi.ReadSingleAsync<AccountSummary>();
var recentTransactions = (await multi.ReadAsync<Transaction>()).ToList();
```

### CancellationToken with Stored Procedures

```csharp
// CancellationToken requires CommandDefinition
var command = new CommandDefinition(
    "Banking.usp_TransferFunds",
    new { FromAccountId = source, ToAccountId = dest, Amount = amount },
    commandType: CommandType.StoredProcedure,
    cancellationToken: cancellationToken);

var result = await connection.QuerySingleOrDefaultAsync<TransferResult>(command);
```

## Transaction Patterns

### IDbTransaction

```csharp
using var connection = new SqlConnection(connectionString);
await connection.OpenAsync(cancellationToken);
using var transaction = await connection.BeginTransactionAsync(cancellationToken);

try
{
    await connection.ExecuteAsync(
        "UPDATE Banking.Account SET Balance = Balance - @Amount WHERE AccountId = @Id",
        new { Amount = amount, Id = sourceId },
        transaction);

    await connection.ExecuteAsync(
        "UPDATE Banking.Account SET Balance = Balance + @Amount WHERE AccountId = @Id",
        new { Amount = amount, Id = destId },
        transaction);

    await transaction.CommitAsync(cancellationToken);
}
catch
{
    await transaction.RollbackAsync(cancellationToken);
    throw;
}
```

### Unit of Work Pattern

```csharp
public interface IUnitOfWork : IAsyncDisposable
{
    IDbConnection Connection { get; }
    IDbTransaction Transaction { get; }
    Task CommitAsync(CancellationToken ct);
}

public class DapperUnitOfWork : IUnitOfWork
{
    public IDbConnection Connection { get; }
    public IDbTransaction Transaction { get; private set; } = null!;

    public DapperUnitOfWork(IDbConnection connection)
    {
        Connection = connection;
        Connection.Open();
        Transaction = Connection.BeginTransaction();
    }

    public async Task CommitAsync(CancellationToken ct)
    {
        await ((DbTransaction)Transaction).CommitAsync(ct);
    }

    public async ValueTask DisposeAsync()
    {
        if (Transaction is not null)
            await ((DbTransaction)Transaction).DisposeAsync();
        if (Connection is not null)
            await ((DbConnection)Connection).DisposeAsync();
    }
}
```

## Custom Type Handlers

```csharp
// Map domain types that Dapper can't handle natively
public class AccountIdTypeHandler : SqlMapper.TypeHandler<AccountId>
{
    public override void SetValue(IDbDataParameter parameter, AccountId value)
    {
        parameter.Value = value.Value;
        parameter.DbType = DbType.Int64;
    }

    public override AccountId Parse(object value) => new((long)value);
}

// Register at startup
SqlMapper.AddTypeHandler(new AccountIdTypeHandler());
```

## Anti-Patterns

### SQL Injection

```csharp
// BAD: String concatenation — SQL injection vulnerability
var sql = $"SELECT * FROM Banking.Account WHERE AccountNumber = '{accountNumber}'";
var account = await connection.QuerySingleOrDefaultAsync<Account>(sql);

// GOOD: Parameterised query
var account = await connection.QuerySingleOrDefaultAsync<Account>(
    "SELECT AccountId, Balance FROM Banking.Account WHERE AccountNumber = @AccountNumber",
    new { AccountNumber = accountNumber });
```

### SELECT *

```csharp
// BAD: Fetches all columns including BLOBs and unused data
var accounts = await connection.QueryAsync<Account>("SELECT * FROM Banking.Account");

// GOOD: Only the columns you need
var accounts = await connection.QueryAsync<Account>(
    "SELECT AccountId, Balance, Status FROM Banking.Account WHERE Status = @Status",
    new { Status = "Active" });
```

### N+1 Queries

```csharp
// BAD: One query per account to get transactions
var accounts = await connection.QueryAsync<Account>(accountSql);
foreach (var account in accounts)
{
    account.Transactions = (await connection.QueryAsync<Transaction>(
        txnSql, new { account.AccountId })).ToList(); // N additional queries!
}

// GOOD: Single query with join or QueryMultiple
var sql = """
    SELECT a.AccountId, a.Balance, t.TransactionId, t.Amount
    FROM Banking.Account a
    LEFT JOIN Banking.Transaction t ON a.AccountId = t.AccountId
    WHERE a.Status = @Status
    """;

var accountDict = new Dictionary<long, Account>();
await connection.QueryAsync<Account, Transaction, Account>(
    sql,
    (account, transaction) =>
    {
        if (!accountDict.TryGetValue(account.AccountId, out var existing))
        {
            existing = account;
            existing.Transactions = new List<Transaction>();
            accountDict[account.AccountId] = existing;
        }
        if (transaction is not null)
            existing.Transactions.Add(transaction);
        return existing;
    },
    new { Status = "Active" },
    splitOn: "TransactionId");
```

## Resilience & Auditability Rules

1. **DECIMAL(19,4) precision** — All monetary parameters must use `decimal` in C# mapped to `DECIMAL(19,4)` in SQL. Never use `double` or `float` for money
2. **Audit columns** — INSERT/UPDATE queries must set audit columns (`CreatedBy`, `CreatedDate`, `ModifiedBy`, `ModifiedDate`) using server-side values (`SYSUTCDATETIME()`) not client-side
3. **Optimistic concurrency** — Updates to critical records should check `RowVersion` and handle `@@ROWCOUNT = 0` (concurrency conflict)
4. **Idempotency checks** — Mutation operations should check for existing idempotency keys before executing (cross-ref `mssql-stored-procedures` skill)

## Review Checklist

### Connection & Lifecycle

- [ ] Connections created with `using` or via DI (Transient lifetime)?
- [ ] No connection caching or singleton connections?
- [ ] Connection strings from configuration (not hardcoded)?

### Queries

- [ ] All queries parameterised (no string concatenation/interpolation)?
- [ ] Specific columns selected (no `SELECT *`)?
- [ ] `QueryAsync` used instead of `Query` for I/O-bound operations?
- [ ] `CancellationToken` propagated via `CommandDefinition`?
- [ ] No N+1 query patterns?

### Stored Procedures

- [ ] `CommandType.StoredProcedure` used for stored procedure calls?
- [ ] `DynamicParameters` used for OUTPUT parameters?
- [ ] C# parameter types match SQL parameter types?

### Transactions

- [ ] Multi-statement writes wrapped in transactions?
- [ ] Transactions committed in try, rolled back in catch?
- [ ] Transaction scope kept minimal?

### Resilience & Auditability

- [ ] `decimal` used for all monetary values?
- [ ] Audit columns set on writes?
- [ ] Optimistic concurrency (RowVersion check) for critical updates?
- [ ] Idempotency key checked before mutation writes?
