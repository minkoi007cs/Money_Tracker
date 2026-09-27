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
- Manual transaction entry for quick tracking on a phone
- Named bank accounts with starting balances; assigned CSV and manual transactions update each account balance
- Installable PWA for iPhone and Android, with a home-screen icon and mobile bottom navigation
- Synthetic demo-data script (clearly labeled as demo data)

## Stack and architecture

`apps/web/`: Next.js App Router, React, TypeScript, Tailwind CSS and PWA assets. `apps/api/`: FastAPI, SQLAlchemy, Alembic and PostgreSQL for deployment. SQLite is the local default. The browser calls a same-origin Next.js API route; that route stores the JWT in an HttpOnly cookie and proxies requests to FastAPI. Business rules stay in the backend. Read [tech.md](./tech.md) for architecture, API and roadmap. **Read [process.md](./process.md) before changing code and update it after significant work or commits.**

## Local setup

Python 3.12+ and Node.js 20.9+ are recommended.

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
cd apps/api
../../.venv/bin/alembic upgrade head
../../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd apps/web
npm install
API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000`. API docs are at `http://127.0.0.1:8000/docs`. Register, add a bank account in Settings, then assign a manual transaction or bank CSV to it. The displayed balance is the starting balance plus all assigned transactions. A synthetic CSV is in `apps/api/tests/fixtures/sample_bank.csv`.

For a populated local demo, after migration run from `apps/api/`:

```bash
DEMO_PASSWORD=choose-your-own-local-password ../../.venv/bin/python scripts/seed_demo.py
```

Log in as `demo@example.com` with the password you chose. The script refuses to run when `APP_ENV=production`.

## Environment

Copy `.env.example` to `.env` and set a strong `JWT_SECRET`. The backend reads environment variables from its process; a `.env` file is a reference for a shell or deployment platform and is not loaded automatically. `DATABASE_URL` defaults to `sqlite:///./money.db` relative to the backend working directory. For PostgreSQL, use `postgresql+psycopg://...`. Set `APP_ENV=production` in production; that mode requires an explicit `JWT_SECRET` of at least 32 characters. Set `API_BASE_URL` on the web project to the API origin. The browser does not need the API URL or JWT. Do not commit real secrets.

## Vercel deployment

Deploy `minkoi007cs/Money_Tracker` as **two Vercel projects** from its `main` branch. The existing `app_system` Vercel project belongs to a different application; do not change its root directory or production branch.

1. Provision a dedicated PostgreSQL database for this app. Save its connection string as `DATABASE_URL` in SQLAlchemy's `postgresql+psycopg://` form. Never use the local SQLite file on Vercel; production startup rejects it.
2. Run migrations against that database from `apps/api/`: `DATABASE_URL='postgresql+psycopg://...' ../../.venv/bin/alembic upgrade head`. Use a secret manager or temporary shell session for the real URL; do not put it in Git.
3. Import the Git repository into Vercel as an API project with **Root Directory** `apps/api`. Vercel detects `index.py` as the FastAPI entrypoint. Set production environment variables `APP_ENV=production`, `DATABASE_URL`, `JWT_SECRET` (random, at least 32 characters), and `CORS_ORIGINS=https://<frontend-domain>`. Deploy and check `https://<api-domain>/health`.
4. Import the same Git repository as a separate Next.js project with **Root Directory** `apps/web`. Set `API_BASE_URL=https://<api-domain>` for Production (and each Preview environment that uses the API). Deploy and check the home page, signup, CSV import and dashboard.
5. Add the final frontend origin to the API project's `CORS_ORIGINS`, then redeploy the API. When a domain or environment variable changes, redeploy the affected project. Keep Preview and Production databases separate.

The API origin is read by the server-side Next.js proxy. The backend requires a durable database and must be migrated before signup/import. Vercel project credentials and database secrets are configured in Vercel, not in this repository.

## Install on a phone

The frontend must be deployed on **HTTPS** with a working API and database. Open its URL on your phone and sign up or sign in. On iPhone, use Safari → Share → Add to Home Screen. On Android, use Chrome → menu → Install app (or Add to Home screen). Chrome may also show an Install app button in Settings. The app needs a connection to load financial data; the offline screen never caches account or transaction responses. It does not connect directly to a bank. Use a CSV statement or enter transactions manually.

## Data rules

Amounts use `Decimal` in Python and `NUMERIC(18,2)` in the database. Positive means money in; negative means money out. Transfers are excluded from income/spending totals, but assigned transfers still affect the bank account balance. Refunds are shown separately. Currencies are never combined or converted. A bank account accepts only transactions in its currency. Existing transactions from earlier versions remain unassigned until new imports or manual entries are assigned. Ambiguous dates require an explicit format. The original CSV is processed in memory and not retained; import metadata and normalized transactions are stored. Uploaded CSVs must be UTF-8/UTF-8 BOM, 10 MiB or less, at most 100,000 rows and 50 columns. Export escapes spreadsheet formula prefixes in text cells.

## Tests

```bash
cd apps/api && ../../.venv/bin/pytest -q
cd ../web && npm run build
```

Backend tests cover import, saved mapping profiles, duplicate detection, category preference, cross-user authorization, account balances and ownership, amount handling, export escaping, deletion, recurring patterns and multi-currency analytics. Frontend production build checks compilation and TypeScript.

## Current limits before public deployment

This is a working local MVP, not a live bank connection. The existing Vercel frontend is not yet connected to an API or database. Authentication uses the local JWT adapter; Supabase Auth is a future integration. The web proxy now uses an HttpOnly, SameSite cookie and checks Origin on writes. Public deployment still needs login rate limiting, configured backups and retention, and PostgreSQL integration/security tests. Exact duplicate fingerprints can classify two genuinely identical charges on the same day as duplicates; users should review import counts. Recurring dates are estimates. CSV encoding beyond UTF-8 and bank-specific import profiles are not yet supported. No direct bank integration, currency conversion or LLM calls are included.
