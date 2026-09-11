# Scaling to 10 Million Users

> How this modular monolith scales — and how to extract microservices when the time comes.

---

## Current Architecture: Single-Process Monolith

Right now, the entire app runs in one Python process. This is **intentional for v1**:

| Component | Current | Why |
|---|---|---|
| App server | Single uvicorn process | Simple to deploy, debug, and profile |
| Database | PostgreSQL 15 | Handles millions of rows comfortably |
| Cache | Redis 7 | Sub-ms reads for balance lookups |
| Event bus | In-process (sync) | Zero infrastructure overhead |
| Module boundaries | Python packages with facade interfaces | Ready for extraction |

**This architecture comfortably handles ~100K users and ~1M expenses.** Beyond that, we need to scale specific bottlenecks.

---

## Phase 1: Vertical Scaling (100K → 1M Users)

### 1.1 Connection Pooling — PgBouncer

**Problem:** Each uvicorn worker holds a DB connection. With 8 workers × 4 replicas = 32 connections, PostgreSQL starts struggling at ~100 connections.

**Solution:** Add PgBouncer as a connection proxy in transaction mode.

```
App (32 workers) → PgBouncer (pool of 20 connections) → PostgreSQL
```

PgBouncer multiplexes 32 worker connections over 20 actual DB connections, reducing PostgreSQL overhead by 40%.

### 1.2 Read Replicas

**Problem:** Balance reads are the most frequent query, and they hit the same DB as writes.

**Solution:** PostgreSQL streaming replication with read replicas.

```
Writes → Primary DB
Reads  → Read Replica(s)
```

SQLAlchemy supports this natively with `create_async_engine` bound to different URLs for read vs. write operations.

### 1.3 Redis Cluster

**Problem:** A single Redis instance is a single point of failure.

**Solution:** Redis Sentinel for HA, or Redis Cluster for sharding. Our cache keys (`balances:group:{group_id}`) are naturally shardable by group_id.

---

## Phase 2: Horizontal Scaling (1M → 10M Users)

### 2.1 Replace the Event Bus: In-Process → Kafka/RabbitMQ

**The interface is already designed for this.** The `IEventBus` abstract class has `subscribe()`, `publish()`, `unsubscribe()`. Swapping `InProcessEventBus` for `KafkaEventBus`:

```python
# Current (in-process)
class InProcessEventBus(IEventBus):
    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[event.event_type]:
            handler(event)

# Future (Kafka)
class KafkaEventBus(IEventBus):
    def publish(self, event: DomainEvent) -> None:
        self._producer.send(event.event_type, event.to_json())
```

**Zero changes to services, routes, or tests.** Only the composition root (`api/app.py`) changes.

### 2.2 Database Partitioning by group_id

**Problem:** At 10M users with 100M+ expenses, single-table queries slow down.

**Solution:** PostgreSQL native partitioning on `group_id`:

```sql
-- Partition expense_expenses by group_id hash
CREATE TABLE expense_expenses (
    ...
) PARTITION BY HASH (group_id);

CREATE TABLE expense_expenses_p0 PARTITION OF expense_expenses
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... 15 more partitions
```

**Why group_id?** Almost every query is scoped to a single group. Partitioning by group_id means each query only scans one partition.

### 2.3 Rate Limiting

**Problem:** AI expense parsing (Claude API) is expensive and slow (~2s per call).

**Solution:** Token bucket rate limiter per user, implemented as a FastAPI middleware:

- 10 AI parse requests per minute per user
- 100 general API requests per minute per user
- Redis-backed counters (we already have Redis)

---

## Phase 3: Microservice Extraction (When Needed)

The modular monolith architecture makes extraction straightforward. Each module has:

1. **A facade (`__init__.py`)** — the public API contract
2. **Private internals** — service, repository, ORM models
3. **Event-based communication** — no direct imports between modules

### Extraction Path

```
┌──────────────────────────────────────────────────────────┐
│  Monolith                                                │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │  User    │  │  Group   │  │ Expense  │  │  Ledger  ││
│  │  Module  │  │  Module  │  │  Module  │  │  Module  ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘│
│       └──────────────┴─────────────┴─────────────┘      │
│                    Event Bus (in-process)                 │
└──────────────────────────────────────────────────────────┘
                          ↓ Extract
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │  Group   │  │ Expense  │  │  Ledger  │
│  Service │  │  Service │  │  Service │  │  Service │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     └──────────────┴─────────────┴─────────────┘
                  Kafka Event Bus
```

**What changes during extraction:**
1. `InProcessEventBus` → `KafkaEventBus`
2. In-process function calls → HTTP/gRPC calls between services
3. Shared PostgreSQL → per-service databases (each module already uses namespaced tables)

**What stays the same:**
1. Service interfaces (`IUserService`, `ILedgerService`, etc.)
2. Domain models (Pydantic DTOs)
3. Business logic (strategies, algorithms)
4. All unit tests

---

## Performance Characteristics

| Operation | Current Performance | At 10M Users |
|---|---|---|
| Create expense | ~50ms (DB write + event bus) | ~80ms (+ Kafka publish) |
| Get group balances (cached) | ~2ms (Redis GET) | ~2ms (Redis Cluster GET) |
| Get group balances (uncached) | ~30ms (DB query) | ~30ms (partitioned query) |
| Debt simplification | ~1ms (O(N log N) in-memory) | ~1ms (same algorithm) |
| Settlement (with lock) | ~40ms (SELECT FOR UPDATE) | ~50ms (same, partitioned) |

---

## Why Not Start with Microservices?

> "If you can't build a modular monolith, you can't build microservices."

1. **Premature distribution** adds network latency, distributed transactions, eventual consistency complexity, and operational overhead — all before you have users.
2. **The modular monolith proves the boundaries work.** If two modules can't be separated in-process, they definitely can't be separated across a network.
3. **Extraction is cheap when boundaries are clean.** The facade pattern means the extraction boundary is already defined.
