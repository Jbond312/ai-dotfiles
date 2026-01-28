---
name: repo-analyzer
description: 'Discover repository conventions and patterns. Use when conventions file is missing, before starting work on a new repository, or when asked to "discover conventions", "analyze repo", or "what patterns does this repo use". Generates .planning/CONVENTIONS.md.'
---

# Repository Analyzer

Discovers how a repository works — its architecture, patterns, conventions, and dependencies. The goal is to understand "how things are done here" so agents can follow existing practices.

## Philosophy

**Discover, don't assume.** Every repository has its own conventions. Rather than looking for specific frameworks, observe what patterns actually exist and document them. If something is unclear, note it as "unclear" rather than guessing.

## When to Run

- First time working in a repository
- When `.planning/CONVENTIONS.md` doesn't exist
- When explicitly asked to refresh conventions

## Discovery Process

Work through each section. For each, explore the codebase and document what you find.

### 1. Solution Overview

```bash
# Find solution and understand structure
find . -name "*.sln" -type f 2>/dev/null
find . -name "*.csproj" -type f 2>/dev/null | head -20

# Check .NET version
grep -h "<TargetFramework" $(find . -name "*.csproj" 2>/dev/null) | head -5
```

**Document:**

- Solution name
- Number and types of projects
- .NET version(s) in use

### 2. Architecture Pattern

Examine the folder structure and project organisation to identify the architectural style.

```bash
# Look at top-level structure
ls -la src/ 2>/dev/null || ls -la
find . -type d -name "Domain" -o -name "Application" -o -name "Infrastructure" -o -name "Features" -o -name "Handlers" 2>/dev/null | head -10
```

**Look for signals:**

| Pattern                          | Signals                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------- |
| **Vertical Slice Architecture**  | `/Features/` folders, handlers grouped by feature, minimal layering          |
| **Clean Architecture**           | `/Domain/`, `/Application/`, `/Infrastructure/`, `/Presentation/` separation |
| **Hexagonal (Ports & Adapters)** | `/Ports/`, `/Adapters/`, clear interface boundaries                          |
| **N-Tier / Layered**             | `/Services/`, `/Repositories/`, `/Controllers/` at same level                |
| **Minimal / Simple**             | Flat structure, few abstractions                                             |

**Document:** The pattern you observe, or "unclear/mixed" if it doesn't fit neatly.

### 3. External Dependencies

Identify what external systems the codebase interacts with.

```bash
# Check package references for common integrations
grep -rh "PackageReference" $(find . -name "*.csproj" 2>/dev/null) | grep -i "entityframework\|dapper\|npgsql\|sqlclient\|azure\|rabbitmq\|masstransit\|kafka\|redis\|mongodb\|http" | sort -u

# Look for connection strings or configuration
grep -rh "ConnectionString\|ServiceBus\|BlobStorage\|CosmosDb" $(find . -name "*.json" -o -name "*.cs" 2>/dev/null) | head -10
```

**Document:**

- Databases (SQL Server, PostgreSQL, CosmosDB, etc.)
- Message brokers (Azure Service Bus, RabbitMQ, Kafka)
- External APIs or services
- Cloud services (Azure Storage, AWS S3, etc.)

### 4. Testing Approach

Examine existing tests to understand how testing is done.

```bash
# Find test projects
find . -name "*Test*.csproj" -o -name "*Tests*.csproj" 2>/dev/null

# Check test framework
grep -rh "xunit\|nunit\|mstest" $(find . -name "*.csproj" 2>/dev/null) | head -3

# Find test files and examine naming
find . -name "*Tests.cs" -o -name "*Test.cs" 2>/dev/null | head -10
```

**Examine 3-5 actual test files** to understand:

- Test class naming (e.g., `{ClassName}Tests`, `{Feature}Tests`)
- Test method naming (e.g., `MethodName_Condition_Result`, `Should_X_When_Y`)
- Assertion style (FluentAssertions, Shouldly, built-in)
- Mocking approach (Moq, NSubstitute, hand-written fakes)
- Test organisation (one class per SUT, feature-based, behaviour-based)

**Document with actual examples** from the codebase.

### 5. Code Patterns

Examine production code to understand common patterns.

```bash
# Look for handler patterns
find . -name "*Handler.cs" -o -name "*Command.cs" -o -name "*Query.cs" 2>/dev/null | head -10

# Check for common libraries
grep -rh "MediatR\|Wolverine\|Result<\|ErrorOr\|FluentValidation\|AutoMapper\|Mapster" $(find . -name "*.cs" 2>/dev/null) | head -10
```

**Examine 3-5 representative files** to understand:

| Aspect                   | What to Look For                                             |
| ------------------------ | ------------------------------------------------------------ |
| **Request handling**     | MediatR, Wolverine, custom handlers, direct controller logic |
| **Validation**           | FluentValidation, DataAnnotations, manual checks             |
| **Error handling**       | Result/ErrorOr types, exceptions, custom error types         |
| **Mapping**              | AutoMapper, Mapster, manual mapping, extension methods       |
| **Dependency injection** | Constructor injection, how dependencies are organised        |

### 6. Code Style

Examine files to understand coding style preferences.

```bash
# Check for nullable, file-scoped namespaces, etc.
head -50 $(find . -name "*.cs" -path "*/src/*" 2>/dev/null | head -3)
```

**Look for:**

- Nullable reference types (`#nullable enable`, `?` on types)
- File-scoped vs block-scoped namespaces
- Primary constructors
- Record types for DTOs
- Expression-bodied members
- Naming conventions (e.g., `_fieldName`, `FieldName`)

### 7. Anything Else Notable

Note anything unusual or project-specific:

- Custom base classes or utilities
- Domain-specific patterns
- Unusual folder structures
- Build or deployment conventions

## Output Format

Create `.planning/CONVENTIONS.md`:

````markdown
# Repository Conventions

> Generated by repo-analyzer on {date}
> Review and adjust if needed. Re-run if conventions change significantly.

## Overview

| Aspect         | Value                  |
| -------------- | ---------------------- |
| Solution       | {name}                 |
| .NET Version   | {version}              |
| Architecture   | {pattern or "unclear"} |
| Test Framework | {framework}            |

## Architecture

{Description of the architectural pattern observed, with folder structure examples}

## External Dependencies

| Type      | Technology                     | Notes       |
| --------- | ------------------------------ | ----------- |
| Database  | {e.g., SQL Server via EF Core} | {any notes} |
| Messaging | {e.g., Azure Service Bus}      | {any notes} |
| ...       | ...                            | ...         |

## Testing Conventions

| Aspect       | Convention                           |
| ------------ | ------------------------------------ |
| Framework    | {xUnit/NUnit/MSTest}                 |
| Assertions   | {FluentAssertions/Shouldly/built-in} |
| Mocking      | {Moq/NSubstitute/none}               |
| Test naming  | {pattern}                            |
| Organisation | {description}                        |

### Example Test

```csharp
// From: {actual file path}
{actual test method showing naming and structure}
```
````

## Code Patterns

| Aspect           | Pattern                                   |
| ---------------- | ----------------------------------------- |
| Request handling | {MediatR/custom handlers/direct/etc.}     |
| Validation       | {FluentValidation/DataAnnotations/manual} |
| Error handling   | {Result type/exceptions/etc.}             |
| Mapping          | {AutoMapper/Mapster/manual/extensions}    |

### Example Handler/Service

```csharp
// From: {actual file path}
{simplified example showing typical structure}
```

## Code Style

| Aspect        | Convention                 |
| ------------- | -------------------------- |
| Nullable refs | {enabled/disabled}         |
| Namespaces    | {file-scoped/block-scoped} |
| Records       | {used for X/not used}      |
| Field naming  | {\_camelCase/other}        |

## Notes

{Anything unusual, unclear, or worth highlighting}

---

## For Agents

When writing code in this repository:

- Follow the patterns shown in examples above
- Match existing test naming: `{pattern with placeholder}`
- Use {error handling approach} for error handling
- {Any other key guidance derived from discoveries}

```

## After Generation

1. Briefly summarise what was discovered
2. Highlight anything ambiguous that might need human clarification
3. The file is ready for agents to reference
```
