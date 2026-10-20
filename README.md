# Where Did My Money Go?

[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-App_Router-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Durable_Store-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

A privacy-first spending dashboard with optional read-only Plaid bank connections and bank CSV imports. It normalizes transactions, categorizes spending, shows month-to-month changes and recurring payments, and gives users control over export and deletion.

## What works

- App System hosted sign-in with email/social providers and short-lived signed access tokens in deployed mode; local email/password mode remains for offline development
- CSV preview, column mapping, saved mapping profiles, signed or separate debit/credit amounts, per-row validation, duplicate detection, import history and deletion
- Merchant normalization, rule-based categories, manual category edits that become user preferences
- Dashboard totals, category and merchant breakdowns, daily spending trend, month comparison and factual insights
- Transaction search, filters, pagination, notes, transfer/refund/subscription flags
- Conservative recurring-payment detection with confidence, estimated next date and user override
- CSV export, deletion of one import, all financial data or the whole account
- Manual transaction entry for quick tracking on a phone
- Optional Plaid Link for checking/savings/credit cards, bank-reported balance snapshots, incremental transaction sync, reconnect and revocation; see [bank setup](./docs/bank-setup.md). Real Chase/PNC access is not yet verified.
- Named manual accounts with starting balances; assigned CSV and manual transactions update each account balance
- Installable PWA for iPhone and Android, with a home-screen icon and mobile bottom navigation
- Synthetic demo-data script (clearly labeled as demo data)

## Stack and architecture

`apps/web/`: Next.js App Router, React, TypeScript, Tailwind CSS and PWA assets. `apps/api/`: FastAPI, SQLAlchemy, Alembic and PostgreSQL for deployment. SQLite is the local default. In deployed mode the browser signs in through App System's hosted authorization-code flow with PKCE; Money Tracker keeps the resulting access and refresh tokens in a same-origin HttpOnly cookie. FastAPI checks the App System JWT signature, issuer and Money Tracker audience. Finance records are stored in a dedicated App System provisioned PostgreSQL tenant database, accessed directly by FastAPI with per-user ownership checks. Read [tech.md](./tech.md) for architecture, API and roadmap. **Read [process.md](./process.md) before changing code and update it after significant work or commits.**

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

Copy `.env.example` to `.env` for reference. The backend reads variables from its process; it does not load `.env` automatically. Local development uses SQLite and a local `JWT_SECRET`. Production requires `APP_ENV=production`, `INFRA_URL`, `INFRA_APP_ID`, `INFRA_SECRET_KEY` and a durable PostgreSQL `DATABASE_URL` in `postgresql+psycopg://...` form. The web project needs `NEXT_PUBLIC_AUTH_MODE=hub`, `INFRA_URL`, `INFRA_PUBLISHABLE_KEY`, `INFRA_SECRET_KEY`, `APP_URL` and `API_BASE_URL`. Only the auth mode is public in the web bundle. Never commit keys or connection strings.

## Vercel deployment

Deploy `minkoi007cs/Money_Tracker` as **two Vercel projects** from its `main` branch. App System remains its own project and serves authentication and database provisioning; do not change its root directory or production branch.

1. In App System, register **Money Tracker** with its exact HTTPS frontend origin, enable hosted sign-in, and provision its own PostgreSQL tenant database. Record the app ID and issue a publishable `pk_` key and server-only `sk_` key. Obtain that tenant database's connection URL without placing it in Git or chat. Do not use App System's Master DB.
2. Run Money Tracker's migrations against the tenant database from `apps/api/`: `DATABASE_URL='postgresql+psycopg://...' ../../.venv/bin/alembic upgrade head`. The real URL belongs in a secret manager or temporary process environment.
3. Import this repository into Vercel as an API project with **Root Directory** `apps/api`. Set `APP_ENV=production`, `DATABASE_URL`, `INFRA_URL=https://system.minkoi.org`, `INFRA_APP_ID`, `INFRA_SECRET_KEY` and `CORS_ORIGINS=https://<frontend-domain>`. Deploy and check `/health`.
4. Keep the existing frontend Vercel project with **Root Directory** `apps/web`. Set `NEXT_PUBLIC_AUTH_MODE=hub`, `INFRA_URL`, `INFRA_PUBLISHABLE_KEY`, `INFRA_SECRET_KEY`, `APP_URL=https://<frontend-domain>` and `API_BASE_URL=https://<api-domain>`. Redeploy so the public auth mode is included in the build.
5. Check hosted sign-in → callback → dashboard → CSV import with synthetic data, a second user's isolation, export and logout on HTTPS. Test iPhone Safari and Android Chrome installation. Keep Preview and Production tenant databases and credentials separate.

The API origin is read by the server-side Next.js proxy. The backend requires a durable database and must be migrated before signup/import. The App System `sk_` key and tenant database URL are server-only. Vercel project credentials and database secrets are configured in Vercel, not in this repository.

## Install on a phone

The frontend must be deployed on **HTTPS** with a working API and database. Open its URL on your phone and sign up or sign in. On iPhone, use Safari → Share → Add to Home Screen. On Android, use Chrome → menu → Install app (or Add to Home screen). Chrome may also show an Install app button in Settings. The app needs a connection to load financial data; the offline screen never caches account or transaction responses. Optional bank connections require Plaid configuration and approved real-bank access; see [bank setup](./docs/bank-setup.md). CSV and manual entry remain available.

## Data rules

Amounts use `Decimal` in Python and `NUMERIC(18,2)` in the database. Positive means money in; negative means money out. Transfers are excluded from income/spending totals, but assigned transfers still affect the bank account balance. Refunds are shown separately. Currencies are never combined or converted. A bank account accepts only transactions in its currency. Existing transactions from earlier versions remain unassigned until new imports or manual entries are assigned. Ambiguous dates require an explicit format. The original CSV is processed in memory and not retained; import metadata and normalized transactions are stored. Uploaded CSVs must be UTF-8/UTF-8 BOM, 10 MiB or less, at most 100,000 rows and 50 columns. Export escapes spreadsheet formula prefixes in text cells.

## Tests

```bash
cd apps/api && ../../.venv/bin/pytest -q
cd ../web && npm run build
```

Backend tests cover import, saved mapping profiles, duplicate detection, category preference, cross-user authorization, account balances and ownership, amount handling, export escaping, deletion, recurring patterns and multi-currency analytics. Frontend production build checks compilation and TypeScript.

## Current limits before public deployment

As of 2026-10-20, the HTTPS production app is live at [Money Tracker](https://money-tracker-rho-bay.vercel.app). Real App System sign-in, protected API access, the dedicated Neon tenant (migration 005), synthetic CSV import, dashboard totals and CSV export passed a browser smoke test; the synthetic records were removed afterward. Backend tests (25), Next.js hub build/TypeScript and root/web dependency audits passed. Manifest and service worker are served; installation on physical iOS/Android devices is still unverified. Plaid Trial is awaiting review (Dashboard estimates 2–3 business days). Bank linking stays disabled until Production access/credentials are configured; real Chase/PNC OAuth, balances and historical transaction sync are not verified. The web proxy uses an HttpOnly, SameSite cookie and checks Origin on writes. Verify backup and retention settings before relying on the app as your only copy of a statement. Exact duplicate fingerprints can classify two genuinely identical charges on the same day as duplicates; review import counts. Recurring dates are estimates. CSV encoding beyond UTF-8 and bank-specific import profiles are not yet supported. Bank snapshots may be cached; no background webhook/cron or forced live-balance request is included. Currency conversion and LLM calls are not included.
