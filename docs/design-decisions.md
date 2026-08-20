# Design Decisions

This document records the *why* behind each significant technical decision in the project.
It's written for two audiences: future maintainers, and interviewers.

---

## 1. Stack: Python + FastAPI + SQLAlchemy 2.0

**Decision**: Python + FastAPI over Node.js/TypeScript or Java/Spring.

**Why FastAPI?**
- Native async support — DB calls don't block the event loop under load
- Pydantic v2 models serve as both request validation AND domain model contracts
- Auto-generated OpenAPI/Swagger docs from route definitions (no extra work)
- First-class support from the Anthropic Python SDK (critical for Prompt 4)

**Why not Node/TypeScript?**
TypeScript's interface system *is* compelling for module contracts, but Python's
Abstract Base Classes (ABC) serve the same purpose. FastAPI's Pydantic models
are more expressive for domain modeling than TypeScript interfaces.

**Why not Java/Spring?**
Spring's annotation-driven magic hides the architectural choices this project
is designed to make explicit. When an interviewer asks "why did you use a facade
pattern?", the answer should be visible in the code — not buried in Spring's
dependency injection container.

---

## 2. Money Representation: `DECIMAL(19, 4)` / Python `Decimal`

**Decision**: Use Python's `decimal.Decimal` in application code, stored as
`NUMERIC(19, 4)` in Postgres.

**The three options:**

| Option | Representation | Pros | Cons |
|---|---|---|---|
| Float | `0.1 + 0.2 = 0.30000000000000004` | Fast | **Wrong for money. Never use.** |
| Integer cents | `$12.50 → 1250` | Exact, Stripe's approach | Non-human-readable in DB, error-prone on boundary |
| Decimal(19,4) | `$12.5000` | Exact, readable, ISO standard | Slightly more storage |

**Why Decimal over integer cents?**
1. The API exposes decimal amounts — converting cents at every boundary is error-prone
2. `DECIMAL(19, 4)` is exact in Postgres — no floating point rounding at the DB layer
3. Python's `decimal.Decimal("0.1") + decimal.Decimal("0.2") == decimal.Decimal("0.3")` — always true
4. 4 decimal places covers multi-currency precision (some currencies have 3 decimal places)

**The rounding rule** (implemented in split strategies, Prompt 2):
When an expense doesn't divide evenly (e.g., $10 / 3 = $3.3333...), we:
1. Round each share to 4 decimal places using `ROUND_HALF_UP`
2. The difference (rounding residual) is added to the *last* participant
3. Assert that `sum(splits) == total_amount` before persisting

This is the standard approach used by Splitwise and Stripe.

---

## 3. Modular Monolith Architecture

**Decision**: Single deployable application, internally structured as isolated modules with clean interface boundaries.

**What this means in practice:**
- Each module exposes one public interface (`IExpenseService`, `ILedgerService`, etc.)
- Modules communicate via the event bus, not direct function calls
- Database tables are namespaced per module (`expense_*`, `ledger_*`, etc.)

**What this enables:**
When the product scales and, say, the expense creation endpoint becomes a bottleneck:
1. Extract `modules/expense/` → its own FastAPI service
2. Move `expense_*` tables to its own Postgres instance
3. Replace `ExpenseService` usages with `ExpenseServiceHttpClient(IExpenseService)`
4. No other module changes

This is the extraction pattern described in Sam Newman's *Building Microservices*.

**What this doesn't mean:**
This is NOT a distributed system. There's no network call between modules.
The facade pattern is an *organisational* constraint, not a runtime one.

---

## 4. Event Bus: In-Process Pub/Sub → Kafka-Ready Interface

**Decision**: Use an in-process synchronous event bus now, with an interface
designed for Kafka migration later.

**Interface contract (IEventBus):**
```python
bus.publish(event: DomainEvent) -> None
bus.subscribe(event_type: str, handler: Callable) -> None
```

**Migration path to Kafka:**
```python
class KafkaEventBus(IEventBus):
    def publish(self, event: DomainEvent) -> None:
        self.producer.send(event.event_type, event)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self.consumer.subscribe([event_type], handler)
```
The only change: `get_event_bus()` returns `KafkaEventBus()`.
Every publisher and subscriber is unaffected.

**Why not Kafka from day 1?**
Kafka adds: ZooKeeper/KRaft, consumer groups, offset management, partition strategy,
dead-letter queues, message schema registry. For a team of one building a portfolio
project, this is pure overhead. Kafka is a scaling solution, not a starting point.

**Synchronous handlers — the tradeoff:**
Current implementation fires handlers in the publisher's call stack.
If `EmailNotifier.notify()` takes 2 seconds, the `POST /expenses` response takes 2 seconds.

Mitigation options (future):
- Option A: Move to Kafka (handlers run in a separate process entirely)
- Option B: Wrap handlers with `asyncio.create_task()` — fire-and-forget

---

## 5. Strategy Pattern for Expense Splitting

**Decision**: Isolate splitting algorithms (`Equal`, `Percent`, `Exact`) behind an `ISplitStrategy` interface.

**Without the Strategy Pattern:**
`ExpenseService` would contain a giant `if / elif` block:
```python
if split_type == "equal":
    # 20 lines of equal split math & rounding
elif split_type == "percent":
    # 20 lines of percent math & validation
elif split_type == "exact":
    # 20 lines of exact math & validation
```
Adding a new "Shares" split type would require modifying `ExpenseService`, violating the **Open/Closed Principle**.

**With the Strategy Pattern:**
`ExpenseService` delegates the math to a factory:
```python
strategy = SplitStrategyFactory.get(request.split_type)
strategy.validate(amount, participants, inputs)
splits = strategy.calculate_splits(amount, participants, inputs)
```
Adding a new split type is a 5-line change: create a new class implementing `ISplitStrategy`, and register it in the `SplitStrategyFactory`. The core `ExpenseService` remains untouched.

---

## 6. Observer Pattern for Notifications

**Decision**: Use an event bus to trigger notifications asynchronously rather than direct function calls.

**Why not direct calls?**
If `ExpenseService` called `EmailNotifier.send()`, adding push notifications later would require modifying `ExpenseService`. Additionally, testing `ExpenseService` would require mocking the email client.

**How it works (Observer/PubSub):**
1. `ExpenseService` publishes `ExpenseCreated`.
2. `EmailNotifier` and `InAppNotifier` subscribe to the event bus.
3. They handle the event independently. 

Adding a new notification channel (e.g., SMS) requires zero changes to the `ExpenseService` or any other module.

---

## 7. Caching Strategy: Write-Invalidate for Balances

*(To be written in Prompt 3 after implementation)*

Section headers:
- Why cache invalidation (delete key) over write-through (update key)
- Why money data makes write-through especially risky (staleness = wrong balance)
- TTL as a safety net, not the primary freshness mechanism

---

## 8. AI Feature: Preview-Only Architecture

*(To be written in Prompt 4 after implementation)*

Section headers:
- Why the LLM cannot auto-commit an expense
- Prompt engineering choices (structured JSON output, member context)
- Where validation happens (application layer, not LLM prompt)

---

## 9. Debt Simplification Algorithm

**Decision**: Implement a Greedy Net-Flow algorithm for debt simplification.

**The Problem**: In a group of 5 people, there might be 10 bilateral debts (A owes B, B owes C, etc.). Settle all debts with the minimum number of transactions.

**Naive Approach**:
Settle each debt individually. This results in $O(N^2)$ transactions. A circular debt (A owes B owes C owes A) wouldn't be simplified.

**Greedy Net-Flow Approach**:
1. Calculate the **net balance** for each person (Total owed to them - Total they owe).
2. Split members into `Creditors` (net > 0) and `Debtors` (net < 0).
3. Put them in two max-heaps based on the absolute net balance.
4. Pop the largest creditor and largest debtor. The debtor pays the creditor the minimum of the two amounts.
5. Push any remaining balance back into the respective heap.
6. Repeat until heaps are empty.

**Why this works**:
This guarantees settling the group in at most $N-1$ transactions. While finding the *absolute minimum* number of transactions is an NP-Complete problem (Subset Sum), this greedy approach runs in $O(N \log N)$ and is identical to the algorithm used by Splitwise in production.
