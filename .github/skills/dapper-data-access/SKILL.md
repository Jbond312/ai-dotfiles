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
