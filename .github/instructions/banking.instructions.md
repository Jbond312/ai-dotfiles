---
applyTo: "**/Features/**/*.cs,**/Domain/**/*.cs,**/Infrastructure/**/*.cs"
description: "Banking domain constraints for production code"
---

# Banking Domain Constraints

## Idempotency

**Mandatory.** Every state-modifying operation must be idempotent. Use idempotency keys for writes. Retrying a failed request must produce the same outcome as a successful single execution.

## Audit

State changes must be traceable. Include correlation IDs in all log entries. Never silently swallow exceptions.

## Data Integrity

Validate inputs at system boundaries. Use database transactions appropriately. Prefer optimistic concurrency with row versioning.

## Batch Processing

Some operations run in batch windows. Design services for both real-time and batch workloads.

## External Dependencies

Stored procedures, external APIs, and message queues require human verification. Flag these in code reviews.
