---
id: "030-event-driven-patterns"
type: "architecture"
created: 2025-12-13
scope: "backend"
---

# 030: Event-Driven Patterns

Kafka is **not** part of the v0.1 MVP by default. Apply this rule set only if/when the project introduces Kafka/event streaming for durable async processing and integrations.

## 1. Event Contract

All Kafka messages **MUST** use the EventEnvelope wrapper:

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class EventEnvelope[T](BaseModel):
    event_id: UUID
    event_type: str              # e.g., "user.created.v1"
    entity_id: str               # Aggregate ID
    timestamp: datetime
    correlation_id: UUID
    causation_id: UUID | None    # Parent event ID
    schema_version: str          # e.g., "1.0.0"
    payload: T

# Usage
envelope = EventEnvelope[UserCreatedV1](
    event_id=uuid4(),
    event_type="user.created.v1",
    entity_id=str(user.id),
    timestamp=datetime.utcnow(),
    correlation_id=correlation_id,
    causation_id=None,
    schema_version="1.0.0",
    payload=UserCreatedV1(user_id=user.id, email=user.email),
)
```

## 2. Domain Events

Define in `domain/{domain}/events.py`:

```python
from pydantic import BaseModel
from uuid import UUID

class UserCreatedV1(BaseModel):
    """Published when a new user is created."""
    user_id: UUID
    email: str

class OrderCompletedV1(BaseModel):
    """Published when an order is marked complete."""
    order_id: UUID
    user_id: UUID
    total_amount: float
```

## 3. Event Publisher Protocol

```python
# protocols.py
class EventPublisherProtocol(Protocol):
    async def publish(
        self,
        event: BaseModel,
        event_type: str,
        entity_id: str,
        correlation_id: UUID,
    ) -> None: ...
```

## 4. Transactional Outbox Pattern

**Problem**: Dual-write inconsistency (DB commit succeeds, Kafka publish fails).

**Solution**: Write events to outbox table in same transaction, relay separately.

```python
# infrastructure/publishers/outbox_publisher.py
class OutboxPublisher(EventPublisherProtocol):
    async def publish(
        self,
        event: BaseModel,
        event_type: str,
        entity_id: str,
        correlation_id: UUID,
    ) -> None:
        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type=event_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
            schema_version="1.0.0",
            payload=event,
        )
        # Insert into outbox table (same transaction as domain changes)
        async with self._session_context() as session:
            outbox_entry = OutboxEntry(
                id=envelope.event_id,
                event_type=event_type,
                payload=envelope.model_dump_json(),
                topic=self._get_topic(event_type),
                created_at=datetime.utcnow(),
            )
            session.add(outbox_entry)
            # Commit happens with domain transaction
```

### Outbox Relay Worker

```python
# workers/outbox_relay.py
async def relay_outbox_events():
    """Background task: poll outbox, publish to Kafka, mark delivered."""
    while True:
        async with session_context() as session:
            entries = await get_pending_outbox_entries(session, limit=100)
            for entry in entries:
                await kafka_producer.send(entry.topic, entry.payload)
                entry.delivered_at = datetime.utcnow()
            await session.commit()
        await asyncio.sleep(1)
```

## 5. Kafka Consumer Pattern

```python
# workers/order_consumer.py
class OrderEventConsumer:
    def __init__(
        self,
        service: OrderServiceProtocol,
        idempotency: IdempotencyProtocol,
    ):
        self._service = service
        self._idempotency = idempotency

    async def handle_message(self, message: bytes) -> None:
        envelope = EventEnvelope.model_validate_json(message)

        # Idempotency check
        if await self._idempotency.is_processed(envelope.event_id):
            return

        # Route by event type
        match envelope.event_type:
            case "payment.completed.v1":
                await self._handle_payment_completed(envelope)
            case _:
                logger.warning(f"Unknown event type: {envelope.event_type}")

        await self._idempotency.mark_processed(envelope.event_id)
```

## 6. Correlation ID Propagation

**Every** operation must propagate correlation ID:

- HTTP requests: Extract from `X-Correlation-ID` header (or generate)
- Kafka messages: Include in EventEnvelope
- Logs: Include as structured field
- Downstream calls: Pass in headers

```python
# middleware/correlation.py
@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
    request.state.correlation_id = UUID(correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

## 7. Topic Naming Convention

```text
{namespace}.{domain}.{event_name}.v{version}

Examples:
- myapp.users.created.v1
- myapp.orders.completed.v1
- myapp.payments.failed.v1
```

## 8. Idempotency (Redis-Backed)

```python
class RedisIdempotency(IdempotencyProtocol):
    async def is_processed(self, event_id: UUID) -> bool:
        return await self._redis.exists(f"processed:{event_id}")

    async def mark_processed(self, event_id: UUID, ttl: int = 86400) -> None:
        await self._redis.setex(f"processed:{event_id}", ttl, "1")
```

TTL should exceed maximum replay window (default: 24 hours).
