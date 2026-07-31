---
type: adr
id: ADR-SKRIPT-0007
title: Defer Kafka/event streaming until it is needed
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0007
---

## Context


Kafka, transactional outbox, and consumer workers add significant operational complexity. The v0.1 MVP is centered on teacher-first discoverability and upload-based script execution, which can run synchronously.

## Decision


- Do not introduce Kafka in v0.1.
- Keep boundaries compatible with future eventing by using protocols for side effects (e.g., publishers) and by avoiding tight coupling between domains.
- Revisit Kafka when we need durable async processing, fan-out integrations, or independent consumers.

## Non-Decisions

No separate non-decisions is stated in the source.

## Consequences


- Faster MVP delivery and lower operational overhead.
- Event-driven patterns can be introduced later without rewriting domain logic.
