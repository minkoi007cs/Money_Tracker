# Where Did My Money Go?

[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-App_Router-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Durable_Store-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

A privacy-first spending dashboard built around bank CSV imports. It normalizes transactions, categorizes spending, shows month-to-month changes and recurring payments, and gives users control over export and deletion.

## What works

- Email/password account with Argon2 password hashing and JWT sessions
- CSV preview, column mapping, saved mapping profiles, signed or separate debit/credit amounts, per-row validation, duplicate detection, import history and deletion
- Merchant normalization, rule-based categories, manual category edits that become user preferences
- Dashboard totals, category and merchant breakdowns, daily spending trend, month comparison and factual insights
- Transaction search, filters, pagination, notes, transfer/refund/subscription flags
- Conservative recurring-payment detection with confidence, estimated next date and user override
- CSV export, deletion of one import, all financial data or the whole account
- Synthetic demo-data script (clearly labeled as demo data)

## Stack and architecture

`frontend/`: Next.js App Router, React, TypeScript, Tailwind CSS. `backend/`: FastAPI, SQLAlchemy, Alembic and PostgreSQL for deployment. SQLite is the local default. The frontend calls the FastAPI REST API; business rules stay in the backend. Read [tech.md](./tech.md) for architecture, API and roadmap. **Read [process.md](./process.md) before changing code and update it after significant work or commits.**

## Local setup

Python 3.12+ and Node.js 20.9+ are recommended.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000`. API docs are at `http://127.0.0.1:8000/docs`. Register a new account, then upload a bank CSV. A synthetic example is in `backend/tests/fixtures/sample_bank.csv`.

For a populated local demo, after migration run from `backend/`:

```bash
DEMO_PASSWORD=choose-your-own-local-password ../.venv/bin/python scripts/seed_demo.py
```

Log in as `demo@example.com` with the password you chose. The script refuses to run when `APP_ENV=production`.

## Environment

Copy `.env.example` to `.env` and set a strong `JWT_SECRET`. The backend reads environment variables from its process; a `.env` file is a reference for a shell or deployment platform and is not loaded automatically. `DATABASE_URL` defaults to `sqlite:///./money.db` relative to the backend working directory. For PostgreSQL, use `postgresql+psycopg://...`. Set `APP_ENV=production` in production; that mode requires an explicit `JWT_SECRET` of at least 32 characters. Set `CORS_ORIGINS` to the exact frontend origin and `NEXT_PUBLIC_API_URL` to the API origin at build time. Do not commit real secrets.

## Vercel deployment

Deploy `minkoi007cs/Money_Tracker` as **two Vercel projects** from its `main` branch. The existing `app_system` Vercel project belongs to a different application; do not change its root directory or production branch.

1. Provision a dedicated PostgreSQL database for this app. Save its connection string as `DATABASE_URL` in SQLAlchemy's `postgresql+psycopg://` form. Never use the local SQLite file on Vercel; production startup rejects it.
2. Run migrations against that database from `backend/`: `DATABASE_URL='postgresql+psycopg://...' ../.venv/bin/alembic upgrade head`. Use a secret manager or temporary shell session for the real URL; do not put it in Git.
3. Import the Git repository into Vercel as an API project with **Root Directory** `backend`. Vercel detects `index.py` as the FastAPI entrypoint. Set production environment variables `APP_ENV=production`, `DATABASE_URL`, `JWT_SECRET` (random, at least 32 characters), and `CORS_ORIGINS=https://<frontend-domain>`. Deploy and check `https://<api-domain>/health`.
4. Import the same Git repository as a separate Next.js project with **Root Directory** `frontend`. Set `NEXT_PUBLIC_API_URL=https://<api-domain>` for Production (and each Preview environment that uses the API). Deploy and check the home page, signup, CSV import and dashboard.
5. Add the final frontend origin to the API project's `CORS_ORIGINS`, then redeploy the API. When a domain or environment variable changes, redeploy the affected project. Keep Preview and Production databases separate.

The frontend API origin is embedded in the browser bundle during build. The backend requires a durable database and must be migrated before signup/import. Vercel project credentials and database secrets are configured in Vercel, not in this repository.

## Data rules

Amounts use `Decimal` in Python and `NUMERIC(18,2)` in the database. Positive means money in; negative means money out. Transfers are excluded from income/spending totals. Refunds are shown separately. Currencies are never combined or converted. Ambiguous dates require an explicit format. The original CSV is processed in memory and not retained; import metadata and normalized transactions are stored. Uploaded CSVs must be UTF-8/UTF-8 BOM, 10 MiB or less, at most 100,000 rows and 50 columns. Export escapes spreadsheet formula prefixes in text cells.

## Tests

```bash
cd backend && ../.venv/bin/pytest -q
cd ../frontend && npm run build
```

Backend tests cover import, saved mapping profiles, duplicate detection, category preference, cross-user authorization, amount handling, export escaping, deletion, recurring patterns and multi-currency analytics. Frontend production build checks compilation and TypeScript.

## Current limits before public deployment

This is a working local MVP, not a deployed banking product. Authentication uses the local JWT adapter; Supabase Auth is a future integration. Sessions are stored in browser localStorage; public deployment should move to secure HttpOnly cookies or an equivalent server-managed session, add login rate limiting and CSRF protection, configure HTTPS and backups, and run PostgreSQL integration/security tests. Exact duplicate fingerprints can classify two genuinely identical charges on the same day as duplicates; users should review import counts. Recurring dates are estimates. CSV encoding beyond UTF-8 and bank-specific import profiles are not yet supported. No direct bank integration, currency conversion or LLM calls are included.
