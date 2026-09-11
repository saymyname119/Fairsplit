# Interview Prep — 5 Hard Questions & Answers

> These are the questions an interviewer would ask about this system design.
> Each answer explains the "what", the "why", and the tradeoff.

---

## Q1: How do you handle the penny rounding problem in expense splitting?

**The problem:** $10 split equally among 3 people = $3.3333... per person. If you round each share to $3.33, the total becomes $9.99 — one cent is lost.

**Our solution: Last-person-absorbs.**

```python
# From modules/expense/strategies.py — EqualSplitStrategy

base_share = (total / count).quantize(Decimal("0.0001"), ROUND_DOWN)
remainder = total - (base_share * count)
# Last person gets the remainder
splits[-1].owed_amount += remainder
```

**How it works:**
1. Divide total by participant count, round DOWN to 4 decimal places
2. Calculate the remainder: `total - (base_share × count)`
3. Add the remainder to the last participant's share
4. **Invariant:** `sum(all_shares) == total` — always true, never off by a penny

**Why DECIMAL(19,4) instead of float?**
```python
>>> 0.1 + 0.2      # float — wrong
0.30000000000000004
>>> Decimal("0.1") + Decimal("0.2")  # Decimal — correct
Decimal('0.3')
```
Floats use binary representation. `0.1` cannot be represented exactly in binary, causing cumulative rounding errors. For money, this is unacceptable.

**Why 4 decimal places, not 2?**
Intermediate calculations (percentages, uneven splits) produce values like `$33.3333`. Rounding to 2 places during calculation loses precision. We keep 4 places internally and round to 2 only for display.

---

## Q2: What's the debt simplification algorithm and its complexity?

**The problem:** In a group of 5 people with 20 expenses, the raw ledger might show 10+ individual debts. The user wants: "What's the minimum number of payments to settle everything?"

**Our algorithm: Greedy Net-Flow (O(N log N))**

```python
# From modules/ledger/service.py — get_simplified_balances()

# Step 1: Calculate net balance for each person
net = defaultdict(Decimal)
for balance in raw_balances:
    net[balance.creditor_id] += balance.net_amount
    net[balance.debtor_id] -= balance.net_amount

# Step 2: Separate into creditors (positive) and debtors (negative)
creditors = sorted(positives, key=lambda x: x[1], reverse=True)  # descending
debtors = sorted(negatives, key=lambda x: x[1])                   # ascending (most negative first)

# Step 3: Greedily match largest creditor with largest debtor
while creditors and debtors:
    settle_amount = min(creditor_amount, abs(debtor_amount))
    # Create a simplified payment: debtor → creditor for settle_amount
    # Reduce both and continue
```

**Why this works:**
- Net balances must sum to zero (conservation of money)
- Matching the largest creditor with the largest debtor minimizes transaction count
- At most N-1 transactions for N people (provably optimal for this greedy approach)

**Complexity:**
- Sorting: O(N log N)
- Matching: O(N)
- Total: **O(N log N)** where N = number of group members

**Interview follow-up — "Is this globally optimal?"**
No. The minimum number of transactions is NP-hard in general (it's equivalent to a bin-packing variant). Our greedy approach gives N-1 transactions in the worst case, which matches Splitwise's production behavior. A globally optimal solution would require exploring all possible payment combinations.

---

## Q3: Why write-invalidate over write-through for the balance cache?

**Context:** When someone creates an expense, we need to update the cached group balances in Redis.

**Three options considered:**

| Strategy | How it works | Risk |
|---|---|---|
| Write-through | Recalculate balance, write to cache AND DB | Cache and DB can diverge if one write fails |
| Write-behind | Write to cache first, flush to DB later | Data loss on crash — unacceptable for money |
| **Write-invalidate** | Delete the cache key on write | Next read recalculates from DB — always fresh |

**Why we chose write-invalidate:**

1. **Correctness > Performance.** A stale balance cache means showing a user the wrong amount of money they owe. With write-invalidate, the next read always comes from the database — there is no window where cache disagrees with DB.

2. **Failure mode is safe.** If the invalidation event is lost (process crash, Redis down), the TTL safety net (300s) guarantees eventual cache expiry. With write-through, a failed cache update means the cache shows stale data indefinitely.

3. **Simplicity.** Invalidation is one `DEL` command. Write-through requires serializing the new balance, atomically updating Redis, and handling partial failure scenarios.

**The cost:** One cache miss (and DB query) after every write operation. In practice, groups have ~5-10 members who check balances occasionally — the miss rate is tiny compared to the read rate.

---

## Q4: How would you extract the ledger module into a microservice?

**The modular monolith was designed for exactly this.** Here's the step-by-step:

### Step 1: Identify the Boundary

The ledger module's facade (`modules/ledger/__init__.py`) already defines the public API:

```python
# Current public interface — this becomes the microservice's HTTP/gRPC API
class ILedgerService:
    async def get_group_balances(group_id) -> list[Balance]
    async def get_simplified_balances(group_id) -> SimplifiedBalanceResult
    async def record_settlement(group_id, request) -> Settlement
    async def handle_expense_created(event) -> None
    async def get_user_balances(user_id) -> UserBalance
```

### Step 2: Replace the Event Bus

```python
# Before (in-process)
bus.subscribe("expense.ExpenseCreated", ledger_service.handle_expense_created)

# After (Kafka)
# Expense Service publishes to topic "expense.ExpenseCreated"
# Ledger Service consumes from topic "expense.ExpenseCreated"
```

The `IEventBus` interface doesn't change. Only the implementation swaps.

### Step 3: Extract the Database

The ledger module already uses namespaced tables (`ledger_balances`, `ledger_settlements`). These move to a separate PostgreSQL instance. No table renaming needed.

### Step 4: Replace In-Process Calls with HTTP/gRPC

```python
# Before (in-process)
from modules.ledger import LedgerService
service = LedgerService(db_session)
balances = await service.get_group_balances(group_id)

# After (HTTP client)
class LedgerClient(ILedgerService):
    async def get_group_balances(self, group_id):
        response = await httpx.get(f"http://ledger-service/groups/{group_id}/balances")
        return [Balance(**b) for b in response.json()]
```

**What stays the same:** All unit tests, domain models, business logic, strategies.
**What changes:** Infrastructure wiring in the composition root.

---

## Q5: How do you prevent race conditions in concurrent settlements?

**The problem:** Two users simultaneously try to settle a $15 debt.

```
User A reads balance: $15      User B reads balance: $15
User A settles $10             User B settles $10
User A writes balance: $5      User B writes balance: $5
                               ← Should be -$5 (overpayment!)
```

**Our solution: SELECT FOR UPDATE (Pessimistic Locking)**

```python
# From modules/ledger/repository.py — get_balance_for_update()

stmt = (
    select(LedgerBalanceORM)
    .where(...)
    .with_for_update()  # ← PostgreSQL row-level lock
)
```

**How it works:**
1. Transaction A calls `SELECT ... FOR UPDATE` — acquires a row-level lock
2. Transaction B calls `SELECT ... FOR UPDATE` — **blocks** until A's transaction completes
3. Transaction A commits (balance = $5)
4. Transaction B now reads the updated balance ($5), sees the $10 settlement would cause overpayment, and raises `ConflictError`

**Why pessimistic over optimistic locking?**
- **Optimistic (version column):** Read row + version, do business logic, write with `WHERE version = X`. If version changed → retry. Good for low contention.
- **Pessimistic (SELECT FOR UPDATE):** Lock the row upfront. Good for high contention on critical data.

We chose pessimistic because:
1. **Money is involved.** A retry that shows "payment failed, try again" is confusing for users and could lead to accidental double payments.
2. **Settlements are rare.** A group settles once a month — the lock duration (~40ms) has negligible impact on throughput.
3. **The lock scope is minimal.** We lock only one row (the specific creditor-debtor balance), not the entire table.

**Interview follow-up — "What about deadlocks?"**
Our lock ordering prevents deadlocks: we always lock the balance row where `creditor_id < debtor_id` (canonical ordering). Two concurrent settlements between the same pair of users will always try to lock the same row in the same order.
