---
name: architecture-patterns
description: "Architecture pattern reference for .NET applications. Use when evaluating, choosing, or reviewing architectural patterns — Vertical Slice, Clean Architecture, CQRS, N-Tier. Triggers on: architecture, vertical slice, clean architecture, CQRS, layers, domain, bounded context, dependency direction, project structure."
---

# Architecture Patterns Reference

**This skill is not prescriptive.** The Repo Analyser discovers which pattern a repository uses, and CONVENTIONS.md documents it. This skill provides reference material for understanding, evaluating, and correctly implementing the pattern that has been chosen.

**Before reviewing:** Read `.planning/CONVENTIONS.md` for the repository's established architecture. Verify code follows that pattern — do not suggest switching patterns mid-project.

## Resilience & Auditability

1. **Domain layer encapsulates critical business rules** — Balance calculations, transfer validation, interest computation, and regulatory checks belong in the domain layer (Clean Architecture) or within the feature handler (Vertical Slice). Never scatter business rules across controllers, services, and repositories
2. **Audit trail favours explicit command/event patterns** — CQRS or handler-per-request patterns naturally produce an audit trail (every mutation is an explicit command). N-Tier services with many methods make auditing harder to enforce consistently
3. **CQRS benefits for reporting** — Separate read models can be optimised for regulatory or compliance report generation without affecting write performance. Read-side projections can serve reporting queries without loading full domain aggregates
4. **Consistency boundaries** — Operations that must be atomic (debit + credit) must live within a single bounded context. Cross-context operations that require atomicity need saga or choreography patterns

## Review Checklist

### Pattern Compliance

- [ ] Code follows the architecture documented in CONVENTIONS.md?
- [ ] New features placed in the correct location per the established pattern?
- [ ] Dependencies point in the correct direction (no outward dependencies from inner layers)?
- [ ] No circular dependencies between components?

### Separation of Concerns

- [ ] Business logic in the appropriate layer (domain/handler, not controller)?
- [ ] Data access in the appropriate layer (infrastructure/repository, not controller)?
- [ ] No "god services" with too many responsibilities?
- [ ] Cross-cutting concerns handled via middleware or behaviours, not duplicated?

### Consistency

- [ ] Same pattern applied across all features in the project?
- [ ] No mixing of architectural patterns within the same bounded context?
- [ ] Naming conventions consistent with the established pattern?

### Resilience & Auditability

- [ ] Critical business rules encapsulated in domain/handler layer?
- [ ] Mutation operations traceable for audit?
- [ ] Consistency boundaries respected for atomic operations?
- [ ] Read models separated from write models where beneficial?
