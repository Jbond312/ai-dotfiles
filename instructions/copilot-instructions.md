# Copilot Instructions

This project uses Azure DevOps for work item tracking and CI/CD. Always check to see if the Azure DevOps MCP server has a tool relevant to the user's request.

## Project Context

This is a .NET 9 banking application with strict requirements around data integrity, auditability, and test coverage. The codebase follows domain-driven design principles and deploys to Azure (AKS, Service Bus, SQL Database).

## Coding Standards

### C# Conventions

Write idiomatic modern C# using the latest language features where they improve clarity. Prefer file-scoped namespaces, primary constructors, and collection expressions. Use `var` when the type is obvious from the right-hand side; use explicit types when it aids readability.

Favour immutability: use `readonly` fields, `init` properties, and records for data transfer objects. Avoid mutable static state entirely—it complicates testing and causes subtle concurrency bugs.

Name things precisely. Methods should be verbs describing what they do (`ProcessPayment`, `ValidateAccount`). Boolean properties and methods should read as questions (`IsValid`, `HasExpired`, `CanProcess`). Avoid abbreviations except for universally understood terms (`Id`, `Url`).

### Banking Domain Constraints

**Idempotency is mandatory.** Every operation that modifies state must be idempotent. Use idempotency keys for all write operations. Design APIs so that retrying a failed request produces the same outcome as a successful single execution.

**Audit everything.** State changes must be traceable. Include correlation IDs in all log entries. Never silently swallow exceptions—log them with context, then handle appropriately.

**Data integrity above all else.** Validate inputs at system boundaries. Use database transactions appropriately. Prefer optimistic concurrency with row versioning over pessimistic locking unless you have measured contention.

**Batch processing awareness.** Some operations run in batch windows. Design services to handle both real-time and batch workloads. Document any timing assumptions.

### Error Handling

Use exceptions for exceptional conditions, not for control flow. Return `Result<T>` or similar discriminated union types for expected failure cases (validation errors, business rule violations).

When catching exceptions, catch the most specific type possible. Always preserve the original exception as an inner exception when rethrowing. Include contextual information in exception messages.

### Async/Await

Use `async`/`await` consistently throughout the call stack. Never block on async code with `.Result` or `.Wait()`—this causes deadlocks. Use `ConfigureAwait(false)` in library code but not in application code that needs the synchronisation context.

Prefer `ValueTask<T>` over `Task<T>` for hot paths where the result is often available synchronously.

## Testing Philosophy

We follow the honeycomb testing model, prioritising integration tests over unit tests. The goal is confidence that the system works correctly, not arbitrary coverage metrics.

### Integration Tests First

Integration tests are the primary validation mechanism. They exercise real behaviour through the Aspire AppHost, hitting actual dependencies (SQL databases in containers, WireMock for external services). A feature is not complete until it has passing integration tests that cover the key scenarios.

**Test-first development:** Write integration tests that define the expected behaviour before or alongside your production code. Tests and implementation are paired—each feature should have corresponding test coverage. The cycle is:

1. Write an integration test describing the behaviour
2. Implement the code to make it pass
3. Refactor while keeping tests green
4. Repeat

### When to Write Unit Tests

Unit tests are appropriate for:

- Complex algorithmic logic with many edge cases
- Pure functions with no dependencies
- Domain model invariant enforcement

Unit tests are not appropriate for:

- Code that primarily coordinates other components
- Simple CRUD operations
- Anything where an integration test provides equal confidence with less coupling to implementation

### Test Structure

Use the Arrange-Act-Assert pattern. Keep the "Arrange" section minimal—if setup is complex, the code under test might have too many dependencies.

Name tests to describe the behaviour: `ProcessPayment_WhenAccountHasInsufficientFunds_ReturnsDeclined`. The test name should make the assertion obvious without reading the code.

### Test Data

Use builders or factory methods for test data, not raw object initialisers scattered throughout tests. This makes tests resilient to constructor changes.

Avoid shared mutable test state. Each test should create its own data and clean up after itself (or use a fresh container).

## Commit Message Format

We use Conventional Commits. Every commit message must follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes only
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration
- `chore`: Other changes that don't modify src or test files

### Scopes

Use the domain or component name as the scope: `payments`, `accounts`, `notifications`, `api`, `infrastructure`.

### Examples

```
feat(payments): add idempotency key validation

fix(accounts): prevent negative balance on concurrent withdrawals

test(payments): add integration tests for refund flow

refactor(api): extract validation into dedicated middleware
```

### Rules

- Subject line must be lowercase
- Subject line must not end with a period
- Subject line should be 50 characters or fewer (hard limit: 72)
- Use imperative mood ("add", not "added" or "adds")
- Body should explain what and why, not how

## Branch Naming

All branches follow the format: `backlog/{workitemnumber}-{short-description}`

The work item number is the Azure DevOps PBI or Spike ID. The description should be lowercase, hyphen-separated, and brief (3-5 words).

Examples:

- `backlog/12345-add-payment-validation`
- `backlog/12346-fix-account-balance-race`

## Agent Workflow

This project uses custom Copilot agents to guide development from work item pickup through to pull request creation. The workflow is:

1. **Work Item Pickup** → Assigns work item, creates branch, summarises scope
2. **Planning** → Creates implementation plan in `.planning/PLAN.md`
3. **Coding** → Implements the plan (TDD or one-shot approach)
4. **Review** → Reviews code before commit
5. **Commit** → Commits with conventional commit message
6. **PR Creation** → Creates draft PR, links work item

### Planning Files

Plans are stored in `.planning/PLAN.md` and tracked using a checklist format. This directory should be gitignored—plans are working documents, not committed artefacts.

The plan tracks:

- Work item context (ID, branch, summary)
- Checklist of implementation tasks with test scenarios
- Work in progress status
- Notes and decisions made during implementation

### Workflow Modes

Two implementation modes are available:

- **TDD (iterative):** Each checklist item is implemented, reviewed, and committed separately. Best for complex or risky changes.
- **One-shot:** All checklist items are implemented together, with a single review and commit. Best for small, well-defined changes.

## Azure DevOps MCP Usage

When interacting with Azure DevOps through the MCP server:

- Use batch tools for multiple updates instead of individual calls
- When getting work items, fetch IDs first, then use `get_work_items_batch_by_ids` for details
- Default fields to display: ID, Type, Title, State
- Present work item results in rendered markdown tables

## Dependencies and Packages

Prefer well-maintained packages with active communities. Check the last commit date and issue response times before adding dependencies.

For Azure services, use the official Azure SDK packages (`Azure.*` namespace). Avoid legacy `Microsoft.Azure.*` packages unless no alternative exists.

Pin major versions in the project file.
