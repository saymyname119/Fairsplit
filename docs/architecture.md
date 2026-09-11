# Architecture — Splitwise Clone

## Overview

This project is a **modular monolith** — a single deployable application internally structured as independent modules with clean boundaries, explicitly designed to be split into microservices without a rewrite.

This is the standard engineering progression at most companies:
1. Start monolith (fast iteration, simple ops)
2. Identify pain points under load (which part scales differently?)
3. Extract the bottleneck module into a service, keeping the interface

This project is at stage 1, with stage 3 already designed.

---

## Module Map

```
/splitwise
├── modules/
│   ├── user/          → Authentication & profiles
│   ├── group/         → Groups & membership
│   ├── expense/       → Expense creation & split calculation
│   ├── ledger/        → Balance calculation & settlements
│   ├── ai/            → NLP expense parsing (Claude API)
│   └── notification/  → Email & in-app notifications (event-driven)
├── shared/
│   ├── events/        → Event bus abstraction
│   ├── db/            → DB engine, session, migrations
│   └── errors/        → Domain error hierarchy
└── api/               → FastAPI routes (thin — no business logic)
```

---

## Module Boundary Rules

**Rule 1: No direct cross-module imports.**
`modules/expense` must never import from `modules/ledger`.
Allowed: `expense` publishes `ExpenseCreated`. `ledger` subscribes to it.

**Rule 2: Only import from a module's `__init__.py` (the facade).**
`from modules.user import User` ✅
`from modules.user.models import UserORM` ❌ — ORM models are private.

**Rule 3: The API layer calls module facades, never module internals.**
Routes import `IUserService`, not `UserRepository`.

These three rules are what makes the "could become microservices" claim credible.

---

## Future Microservice Map

| Module | Future Service Name | Own DB? | Comms Pattern |
|---|---|---|---|
| `user` | `user-service` | Yes — user_accounts table | REST / gRPC |
| `group` | `group-service` | Yes — group_groups, group_members | REST |
| `expense` | `expense-service` | Yes — expense_expenses, expense_splits | REST + Kafka events |
| `ledger` | `ledger-service` | Yes — ledger_balances, ledger_settlements | REST (reads) + Kafka (writes) |
| `ai` | `ai-service` | No — stateless; calls Claude API | REST |
| `notification` | `notification-service` | Optional — notification log | Kafka consumer |

---

## Request Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API Layer (FastAPI)
    participant ES as ExpenseService
    participant LS as LedgerService
    participant Bus as EventBus
    participant NS as NotificationService
    participant Cache as Redis

    C->>API: POST /groups/:id/expenses
    API->>ES: create_expense(group_id, request)
    ES->>ES: validate participants are members
    ES->>ES: select SplitStrategy, calculate splits
    ES->>DB: INSERT expense + splits (transaction)
    ES->>Bus: publish(ExpenseCreated)
    Bus->>LS: handle_expense_created(expense_id)
    LS->>DB: UPDATE ledger_balances (net balance)
    LS->>Cache: DELETE balances:group:{group_id}
    Bus->>NS: notify(ExpenseCreated)
    NS->>NS: EmailNotifier.notify(), InAppNotifier.notify()
    ES-->>API: Expense (domain model)
    API-->>C: 201 Created
```

---

## Infrastructure

```mermaid
graph TB
    Client([Client / Browser])
    API[FastAPI App]
    PG[(Postgres 15)]
    Redis[(Redis 7)]
    Claude[Claude API\nexternal]

    Client --> API
    API --> PG
    API --> Redis
    API --> Claude
```

---

## Database Schema (Namespaced Tables)

```
user_accounts           ← users
group_groups            ← groups
group_members           ← group ↔ user junction
expense_expenses        ← expense header
expense_splits          ← one row per participant per expense
ledger_balances         ← net balance per user-pair per group
ledger_settlements      ← immutable settlement records
```

All monetary columns: `DECIMAL(19, 4)` — exact arithmetic, no float errors.

---

## Key Indexes and Why

| Table | Index | Rationale |
|---|---|---|
| `user_accounts` | `email` (unique) | Login lookup: O(log N) |
| `group_members` | `(group_id)` | "all members of group G" — called on every expense creation |
| `group_members` | `(user_id)` | "all groups for user U" — user dashboard |
| `expense_expenses` | `(group_id, created_at DESC)` | Paginated expense list |
| `expense_splits` | `(group_id, user_id)` | **Core ledger read** — "what does user U owe in group G?" |
| `ledger_balances` | `(group_id, creditor_id)` | Balance view query |
| `ledger_balances` | unique `(group_id, creditor_id, debtor_id)` | One row per pair — enforced at DB |

---

## Monolith-First Rationale

> "Monolith first, microservices never (unless you hit a real bottleneck)."
> — Martin Fowler

Running microservices from day 1 adds:
- Network latency between every module call
- Distributed transaction complexity (2-phase commit or saga pattern)
- Independent deployment pipelines per service
- Service discovery, load balancing, TLS between services

For a product at 0 users, none of these costs are justified.
This monolith is structured to make the extraction cost near-zero *when* (not if) it's needed.

---

## How This Scales to 10M Users

See `docs/scaling.md` — this section is intentionally brief here to keep the architecture document focused on the current design.

Short version:
1. **Read replicas** for balance queries (currently the highest-read endpoint)
2. **Redis cluster** for distributed caching
3. **Kafka** replaces the in-process event bus — one consumer group per subscriber module
4. **Sharding by group_id** — all expense and ledger data for a group lives on one shard
5. **Module extraction** — ledger-service first (independent scaling of reads vs writes)

---

## Module Dependency Graph

```mermaid
graph TD
    API["API Layer (Routes)"]
    User["User Module"]
    Group["Group Module"]
    Expense["Expense Module"]
    Ledger["Ledger Module"]
    Notif["Notification Module"]
    AI["AI Module"]
    Bus["Event Bus"]
    Cache["Redis Cache"]
    DB["PostgreSQL"]

    API --> User
    API --> Group
    API --> Expense
    API --> Ledger
    API --> AI
    API --> Cache

    Expense -->|"publishes ExpenseCreated"| Bus
    Group -->|"publishes MemberAdded"| Bus
    Bus -->|"subscribes"| Ledger
    Bus -->|"subscribes"| Notif
    Bus -->|"invalidates cache"| Cache

    User --> DB
    Group --> DB
    Expense --> DB
    Ledger --> DB

    AI -->|"Claude API"| External["External API"]

    style Bus fill:#f9f,stroke:#333
    style Cache fill:#ff9,stroke:#333
    style DB fill:#9cf,stroke:#333
```

---

## Database ER Diagram

```mermaid
erDiagram
    user_accounts {
        string id PK
        string email UK
        string name
        string hashed_password
        boolean is_active
        datetime created_at
        datetime deleted_at
    }

    group_groups {
        string id PK
        string name
        string description
        string created_by_id FK
        datetime created_at
        datetime deleted_at
    }

    group_members {
        string id PK
        string group_id FK
        string user_id FK
        string role
        datetime created_at
    }

    expense_expenses {
        string id PK
        string group_id FK
        string paid_by_id FK
        decimal amount
        string description
        string split_type
        datetime created_at
        datetime deleted_at
    }

    expense_splits {
        string id PK
        string expense_id FK
        string user_id FK
        string group_id FK
        decimal owed_amount
        decimal percentage
    }

    ledger_balances {
        string id PK
        string group_id FK
        string creditor_id FK
        string debtor_id FK
        decimal net_amount
    }

    ledger_settlements {
        string id PK
        string group_id FK
        string from_user_id FK
        string to_user_id FK
        decimal amount
        datetime created_at
    }

    user_accounts ||--o{ group_groups : "creates"
    user_accounts ||--o{ group_members : "joins"
    group_groups ||--o{ group_members : "has"
    group_groups ||--o{ expense_expenses : "contains"
    user_accounts ||--o{ expense_expenses : "pays"
    expense_expenses ||--o{ expense_splits : "split into"
    group_groups ||--o{ ledger_balances : "tracks"
    group_groups ||--o{ ledger_settlements : "settles in"
```

---

## Cache Invalidation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API Layer
    participant Redis as Redis Cache
    participant LS as LedgerService
    participant DB as PostgreSQL

    Note over C, DB: Read Path (Cache Hit)
    C->>API: GET /groups/:id/balances
    API->>Redis: GET balances:group:{id}
    Redis-->>API: cached data ✓
    API-->>C: 200 OK (from cache)

    Note over C, DB: Read Path (Cache Miss)
    C->>API: GET /groups/:id/balances
    API->>Redis: GET balances:group:{id}
    Redis-->>API: null (miss)
    API->>LS: get_group_balances(id)
    LS->>DB: SELECT from ledger_balances
    DB-->>LS: balance rows
    LS-->>API: list[Balance]
    API->>Redis: SET balances:group:{id} (TTL=300s)
    API-->>C: 200 OK (from DB)

    Note over C, DB: Write Path (Invalidation)
    C->>API: POST /groups/:id/expenses
    API->>DB: INSERT expense + splits
    API->>Redis: DEL balances:group:{id}
    Note right of Redis: Next read will<br/>recalculate from DB
```

