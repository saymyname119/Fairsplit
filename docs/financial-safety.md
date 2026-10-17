# Financial safety

Run `alembic upgrade head` before starting the updated API. Revision 0003 adds
versioned group state, the immutable journal, settlement retry keys, notification
jobs and delivered in-app notifications. Existing pair balances become explicit
opening-balance journal postings; historical transactions are not reconstructed.

## Money and journal

Each journal row contains equal and opposite account legs. `GET
/groups/{id}/journal` exposes both signed postings. Expenses append postings;
edits and deletions append compensating balance adjustments. Settlements and
reversals append postings too. PostgreSQL triggers reject updates, deletes and
truncation of journal and settlement records. Pair balances are a mutable read
projection and can be rebuilt from active expense splits and signed settlements.
Money uses Decimal and NUMERIC(19,4). Editing amounts preserves the original
split proportions and assigns rounding residuals to the last participant.

Greedy simplification preserves net balances in O(N log N). It reduces transfers
but does not guarantee the globally minimum number for every possible input.
Payments from its plan may connect users without a direct bilateral expense.

## Confirmation and retries

All expense routes, settlements, reversals and recalculations lock a stable
`ledger_state` row before changing financial data. This serializes writes within
a group, including the first expense when no pair rows exist, while allowing
unrelated groups to proceed independently. Pair locks follow deterministic order.

`GET /groups/{id}/balances/simplified` returns `version`. Send that captured value
as `expected_version` plus a unique `idempotency_key` to `POST /groups/{id}/settle`.
Both fields are required. Stale confirmations return 409. Retry the exact payment
with the same key: it returns the existing record even after the version changes.
Reusing a key for different payment details returns 409. The browser retains its
key after a failed request and disables the confirm button while saving.

`GET /groups/{id}/settlements` lists history. `POST
/groups/{id}/settlements/{settlement_id}/reverse` accepts the same version and key
fields. A reversal adds a negative settlement linked to its original, restores
the debt and can happen only once. Group members can record payments and reverse
them. All financial endpoints require group membership.

## Cache and notification recovery

Balance cache keys include the committed group version. Readers acquire the
same group lock before reading the version and balances, so an old reader cannot
populate the cache for a later revision. Redis errors fall through to PostgreSQL;
old revision keys expire through the configured TTL.

Financial notification jobs are committed atomically with ledger changes. The
API starts an asynchronous worker which claims batches with `FOR UPDATE SKIP
LOCKED`. Delivery writes an in-app notification and acknowledges its job in the
same database transaction. A crash before commit rolls back both, allowing
another worker to retry without duplicate delivery. Failed jobs use capped
exponential backoff. Pending jobs survive API restarts. This queue delivers
in-app notifications; it does not claim guaranteed external email delivery.
`GET /groups/{id}/notifications` returns the current member's notifications.

## Verification

Run `pytest tests/unit` and `npm run build` in frontend. Real PostgreSQL tests:

```powershell
$env:FAIRSPLIT_TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost/test_db"
pytest tests/integration/test_financial_safety.py
```

Use a disposable database migrated through 0003. Tests cover parallel duplicate
requests, stale confirmations, mismatched retry payloads, concurrent first
expenses, indirect settlements, reversal replay, immutable journal enforcement,
expense edit/delete invariants and recovery after a worker crash. They create
unique groups and retain audit records because the database forbids deletion.
