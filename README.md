# FairSplit

FairSplit helps groups track shared expenses, see who owes what, and record payments.
Use it for trips, shared homes, or everyday expenses with friends.

## Features

- Email/password accounts and Google sign-in through Supabase Auth.
- Groups, member management, and invitations by email or shareable link.
- Expenses with equal, exact-amount, or percentage splits.
- Group currencies: USD, EUR, GBP, JPY, and INR.
- Balances and suggested payments to simplify settling up.
- Partial payments, payment history, and reversals.
- AI expense previews that require confirmation before saving (optional).
- Password recovery by email (optional).

FairSplit records payments; it does not transfer money. Each group uses one currency;
there is no exchange-rate conversion. AI parsing and email delivery require the
provider credentials described below.

## Stack

React, TypeScript, and Vite on the frontend; Python, FastAPI, SQLAlchemy, PostgreSQL,
and Redis on the backend. Alembic manages schema migrations. Supabase provides
optional Google authentication and can host the PostgreSQL database.

## Run locally

Requirements: Python 3.11+, Node.js 22.12+, PostgreSQL, and Redis.
Docker Compose can supply the local database and cache.

### 1. Prepare the backend

From the repository root:

```sh
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

Install dependencies and copy `.env.example` to `.env`:

```sh
python -m pip install -e ".[dev]"
```

For local PostgreSQL and Redis:

```sh
docker compose up -d postgres redis
```

Set these values in the root `.env`:

```dotenv
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://splitwise:splitwise@localhost:5432/splitwise
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=replace-with-a-generated-secret
APP_BASE_URL=http://127.0.0.1:5173
```

Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
For Supabase PostgreSQL, replace `DATABASE_URL` with your project's connection
string using the `postgresql+asyncpg://` scheme. Redis is still required; start
only the `redis` Compose service if you use a hosted database.

Apply migrations and start the API:

```sh
alembic upgrade head
uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the frontend

Copy `frontend/.env.example` to `frontend/.env` and set:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
```

In a separate terminal:

```sh
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open [FairSplit](http://127.0.0.1:5173/). API documentation is available at
[Swagger UI](http://127.0.0.1:8000/docs), and service health at
[/healthz](http://127.0.0.1:8000/healthz).

## Optional services

### Google sign-in

Enable the Google provider in Supabase Auth and configure its Google OAuth client.
Allow your frontend URL in Supabase's authentication redirect settings.

Root `.env`:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
```

`frontend/.env`:

```dotenv
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
```

Use the same Supabase project on both sides. The backend verifies the Supabase
access token before issuing an app session. Never put a service-role key or
Google client secret in frontend settings. Restart services after changing settings.

### AI expense previews

Set `CLAUDE_API_KEY` in the root `.env`; `CLAUDE_MODEL` selects the model.
Choose **Preview with AI** in the expense dialog, review the payer, participants,
amount, and split, then confirm to save. Manual entry works without an AI key.

### Email invitations and password recovery

Configure either SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM_EMAIL`) or Resend (`RESEND_API_KEY`, `RESEND_FROM_EMAIL`) in the root
`.env`. Set `APP_BASE_URL` to the frontend address used by recipients.

Password reset links expire after 30 minutes and can be used once. A password
change invalidates older app sessions. Without an email provider, password
recovery is unavailable; invitation links can still be shared manually.

## Checks

With the Python environment activated, from the repository root:

```sh
pytest tests/unit
node --test frontend/tests/session.test.mjs
npm --prefix frontend run build
```

Database regression tests require a **disposable PostgreSQL database** migrated
with `alembic upgrade head`. Set `DATABASE_URL` to that database while migrating,
and set `FAIRSPLIT_TEST_DATABASE_URL` to its async connection string when testing:

```sh
pytest tests/integration/test_feature_completion.py tests/integration/test_financial_safety.py
```

These tests create records. Use a dedicated test database.

## Project layout

| Directory | Purpose |
| --- | --- |
| `frontend/` | React app and frontend session tests |
| `api/` | FastAPI routes and authentication |
| `modules/` | Users, groups, expenses, balances, notifications, and AI |
| `shared/` | Configuration, database, cache, events, and errors |
| `shared/db/migrations/` | Alembic schema migrations |
| `tests/` | Backend unit and integration tests |
| `docs/` | Architecture and implementation details |

See [financial safety](docs/financial-safety.md) for payment idempotency, journal
records, and concurrency checks, and [architecture](docs/architecture.md) for the
module structure. Keep `.env` files out of version control.
