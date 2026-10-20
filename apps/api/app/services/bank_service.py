"""Read-only Plaid integration. Secrets stay server-side; sync and cursor commit together."""
import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from fastapi import HTTPException
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from ..importer import merchant_and_category, normalize_description
from ..models import Account, BankConnection, MerchantPreference, Transaction, utcnow


class PlaidError(Exception):
    def __init__(self, code):
        self.code = code


def cipher():
    try:
        keys = os.environ["BANK_TOKEN_ENCRYPTION_KEYS"].split(",")
        return MultiFernet([Fernet(key.strip().encode()) for key in keys])
    except (KeyError, ValueError):
        raise HTTPException(503, "Bank connections need server configuration")


def config():
    env = os.getenv("PLAID_ENV", "sandbox")
    if env not in ("sandbox", "production"):
        raise HTTPException(503, "Invalid bank connection environment")
    if not os.getenv("PLAID_CLIENT_ID") or not os.getenv("PLAID_SECRET"):
        raise HTTPException(503, "Bank connections have not been enabled yet")
    cipher()
    return env


def plaid(path, **payload):
    env = config()
    try:
        response = httpx.post(
            f"https://{env}.plaid.com/{path}",
            json={"client_id": os.environ["PLAID_CLIENT_ID"], "secret": os.environ["PLAID_SECRET"], **payload},
            headers={"Plaid-Version": "2020-09-14"}, timeout=15,
        )
        body = response.json()
    except (httpx.HTTPError, ValueError):
        raise PlaidError("PROVIDER_UNAVAILABLE")
    if not response.is_success:
        code = body.get("error_code", "PROVIDER_UNAVAILABLE")
        # Never return/log provider messages, request bodies or credentials.
        raise PlaidError(code if isinstance(code, str) and len(code) < 100 else "PROVIDER_UNAVAILABLE")
    return body


def token(connection):
    if connection.environment != config():
        raise HTTPException(409, "This bank connection belongs to a different environment")
    try:
        return cipher().decrypt(connection.access_token_encrypted.encode()).decode()
    except (InvalidToken, AttributeError):
        raise HTTPException(503, "Bank credential cannot be read; check the server encryption keys")


def timestamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def public_connection(connection):
    return {
        "id": connection.id, "institution_name": connection.institution_name,
        "environment": connection.environment, "status": connection.status,
        "history_ready": connection.history_ready, "error_code": connection.error_code,
        "last_synced_at": timestamp(connection.last_synced_at),
    }


def owned_connection(db, user_id, connection_id):
    connection = db.scalar(select(BankConnection).where(BankConnection.id == connection_id, BankConnection.user_id == user_id))
    if not connection:
        raise HTTPException(404, "Bank connection not found")
    return connection


def create_link_token(user_id, connection=None):
    redirect = os.getenv("PLAID_REDIRECT_URI", "")
    if not redirect or (not redirect.startswith("https://") and not (config() == "sandbox" and redirect.startswith("http://localhost:"))):
        raise HTTPException(503, "Configure the bank OAuth redirect URL on the server")
    payload = {
        "user": {"client_user_id": user_id}, "client_name": "Money Tracker",
        "country_codes": ["US"], "language": "en", "redirect_uri": redirect,
    }
    if connection:
        payload["access_token"] = token(connection)
    else:
        payload.update(products=["transactions"], transactions={"days_requested": 365},
                       account_filters={"depository": {"account_subtypes": ["checking", "savings"]},
                                        "credit": {"account_subtypes": ["credit card"]}})
    try:
        result = plaid("link/token/create", **payload)
    except PlaidError:
        raise HTTPException(503, "Could not start bank sign-in. Check Plaid access and try again.")
    return {"link_token": result["link_token"], "environment": config()}


def decimal_balance(value):
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.01"))


def save_accounts(db, connection, records):
    now = utcnow()
    for record in records:
        if record.get("type") not in ("depository", "credit"):
            continue
        balances = record["balances"]
        currency = balances.get("iso_currency_code")
        if not currency or len(currency) != 3:
            raise PlaidError("UNSUPPORTED_CURRENCY")
        account = db.scalar(select(Account).where(Account.external_account_id == record["account_id"]))
        if account and (account.user_id != connection.user_id or account.bank_connection_id != connection.id):
            raise PlaidError("ACCOUNT_CONFLICT")
        if not account:
            account = Account(user_id=connection.user_id, bank_connection_id=connection.id,
                              external_account_id=record["account_id"], opening_balance=Decimal("0"))
            db.add(account)
        account.name = f"{connection.institution_name} · {record.get('name', 'Account')}"[:100]
        account.currency = currency
        account.account_type = record["type"]
        account.mask = (record.get("mask") or "")[:10]
        account.bank_balance = decimal_balance(balances.get("current"))
        account.available_balance = decimal_balance(balances.get("available"))
        account.balance_fetched_at = now
    db.flush()


def exchange(db, user_id, public_token):
    access = None
    saved = False
    try:
        result = plaid("item/public_token/exchange", public_token=public_token)
        access = result["access_token"]
        data = plaid("accounts/get", access_token=access)
        item = data["item"]
        institution_id = item.get("institution_id")
        if not institution_id:
            raise HTTPException(400, "The bank did not supply an institution identifier")
        institution_name = item.get("institution_name")
        if not institution_name:
            institution_name = plaid("institutions/get_by_id", institution_id=institution_id, country_codes=["US"])["institution"]["name"]
        existing = db.scalar(select(BankConnection).where(
            BankConnection.user_id == user_id, BankConnection.institution_id == institution_id,
            BankConnection.environment == config(),
        ))
        if existing:
            # Do not revoke an existing token if the provider returned the same Item.
            if existing.item_id == result["item_id"]:
                access = None
            raise HTTPException(409, "This bank is already connected. Use Reconnect on the existing connection.")
        connection = BankConnection(
            user_id=user_id, item_id=result["item_id"], environment=config(),
            institution_id=institution_id, institution_name=institution_name[:100],
            access_token_encrypted=cipher().encrypt(access.encode()).decode(),
        )
        db.add(connection)
        db.flush()
        save_accounts(db, connection, data["accounts"])
        if not db.scalar(select(Account.id).where(Account.bank_connection_id == connection.id)):
            raise HTTPException(400, "Select a checking, savings or credit card account with transaction access")
        db.commit()
        saved = True
        return public_connection(connection)
    except IntegrityError:
        raise HTTPException(409, "This bank was already linked. Refresh your connections.")
    except PlaidError:
        raise HTTPException(503, "Bank connection could not be completed. Try again from Connect bank.")
    finally:
        if not saved:
            db.rollback()
            if access:
                try:
                    plaid("item/remove", access_token=access)
                except PlaidError:
                    pass


def upsert_transaction(db, connection, record):
    account = db.scalar(select(Account).where(Account.bank_connection_id == connection.id,
        Account.user_id == connection.user_id, Account.external_account_id == record["account_id"]))
    if not account:
        # Never advance the cursor past transactions from unknown accounts.
        raise PlaidError("ACCOUNT_NOT_AVAILABLE")
    pending_id = record.get("pending_transaction_id")
    predecessor = None
    if pending_id:
        predecessor = db.scalar(select(Transaction).where(Transaction.bank_connection_id == connection.id,
            Transaction.external_transaction_id == pending_id, Transaction.pending.is_(True)))
        db.execute(delete(Transaction).where(Transaction.bank_connection_id == connection.id,
            Transaction.external_transaction_id == pending_id, Transaction.pending.is_(True)))
    existing = db.scalar(select(Transaction).where(Transaction.external_transaction_id == record["transaction_id"]))
    if existing and (existing.user_id != connection.user_id or existing.bank_connection_id != connection.id):
        raise PlaidError("TRANSACTION_CONFLICT")
    if not existing:
        existing = Transaction(user_id=connection.user_id, bank_connection_id=connection.id,
            external_transaction_id=record["transaction_id"], notes="",
            fingerprint=hashlib.sha256(f"plaid|{connection.id}|{record['transaction_id']}".encode()).hexdigest(),
            bank_overrides="[]")
        if predecessor:
            existing.bank_overrides = predecessor.bank_overrides
            existing.notes = predecessor.notes
            for field in json.loads(predecessor.bank_overrides or "[]"):
                setattr(existing, field, getattr(predecessor, field))
        db.add(existing)
    overrides = set(json.loads(existing.bank_overrides or "[]"))
    amount = -Decimal(str(record["amount"]))  # Plaid: positive = money out.
    raw = record.get("original_description") or record.get("name") or "Bank transaction"
    merchant, category, confidence = merchant_and_category(raw, record.get("merchant_name"), amount)
    pfc = record.get("personal_finance_category") or {}
    primary, detailed = pfc.get("primary", ""), pfc.get("detailed", "")
    category_map = {
        "INCOME": "Income", "FOOD_AND_DRINK": "Food & Dining", "GENERAL_MERCHANDISE": "Shopping",
        "TRANSPORTATION": "Transportation", "TRAVEL": "Travel", "ENTERTAINMENT": "Entertainment",
        "MEDICAL": "Health", "PERSONAL_CARE": "Personal Care", "RENT_AND_UTILITIES": "Utilities",
        "BANK_FEES": "Fees", "HOME_IMPROVEMENT": "Housing",
    }
    category = category_map.get(primary, category)
    if detailed.endswith("GROCERIES"):
        category = "Groceries"
    if detailed.endswith("RENT"):
        category = "Housing"
    transfer = primary in ("TRANSFER_IN", "TRANSFER_OUT", "LOAN_PAYMENTS") or "CREDIT_CARD_PAYMENT" in detailed
    # Loan principal/credit-card payments are transfers; fees/interest retain their own categories.
    if transfer:
        category = "Transfers"
    preference = db.scalar(select(MerchantPreference).where(
        MerchantPreference.user_id == connection.user_id, MerchantPreference.merchant_key == merchant.casefold()))
    values = {
        "account_id": account.id, "transaction_date": date.fromisoformat(record["date"]),
        "description_raw": raw, "description_normalized": normalize_description(raw),
        "amount": amount, "currency": record.get("iso_currency_code") or account.currency,
        "pending": bool(record.get("pending")), "merchant_name": merchant,
        "category": preference.category if preference else category,
        "category_source": "preference" if preference else "bank", "confidence": Decimal("1") if preference else confidence,
        "is_transfer": transfer, "is_refund": amount > 0 and ("REFUND" in detailed or "REFUND" in normalize_description(raw)),
        "is_subscription": category == "Subscriptions",
    }
    if values["currency"] != account.currency:
        raise PlaidError("UNSUPPORTED_CURRENCY")
    for key, value in values.items():
        if key not in overrides:
            setattr(existing, key, value)
    db.flush()


def sync(db, connection, force=False):
    now = utcnow()
    last = connection.last_synced_at
    interval = 300 if connection.history_ready else 10
    if not force and last and (now - last.replace(tzinfo=timezone.utc)).total_seconds() < interval:
        return {**public_connection(connection), "skipped": True}
    if connection.status != "connected":
        return {**public_connection(connection), "skipped": True}
    # A database lease serializes sync across serverless workers, tabs and devices.
    lease = now + timedelta(minutes=5)
    acquired = db.execute(update(BankConnection).where(BankConnection.id == connection.id,
        or_(BankConnection.sync_lock_until.is_(None), BankConnection.sync_lock_until < now)).values(sync_lock_until=lease).execution_options(synchronize_session=False))
    db.commit()
    if acquired.rowcount != 1:
        return {**public_connection(connection), "skipped": True}
    db.refresh(connection)
    started = time.monotonic()
    try:
        access = token(connection)
        data = plaid("accounts/get", access_token=access)
        save_accounts(db, connection, data["accounts"])
        original_cursor = connection.cursor
        for attempt in range(3):
            cursor = original_cursor
            pages = []
            try:
                for _ in range(100):
                    if time.monotonic() - started > 75:
                        raise PlaidError("SYNC_RETRY_REQUIRED")
                    payload = {"access_token": access, "count": 500, "options": {"include_original_description": True}}
                    if cursor:
                        payload["cursor"] = cursor
                    page = plaid("transactions/sync", **payload)
                    pages.append(page)
                    cursor = page["next_cursor"]
                    if not page["has_more"]:
                        break
                else:
                    raise PlaidError("SYNC_RETRY_REQUIRED")
                break
            except PlaidError as exc:
                if exc.code != "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION" or attempt == 2:
                    raise
        for page in pages:
            for record in page["added"] + page["modified"]:
                upsert_transaction(db, connection, record)
            for record in page["removed"]:
                db.execute(delete(Transaction).where(Transaction.bank_connection_id == connection.id,
                    Transaction.external_transaction_id == record["transaction_id"]))
        connection.cursor = cursor
        connection.history_ready = connection.history_ready or pages[-1].get("transactions_update_status") == "HISTORICAL_UPDATE_COMPLETE"
        connection.last_synced_at = utcnow()
        connection.error_code = None
        connection.sync_lock_until = None
        db.commit()
        return {**public_connection(connection), "skipped": False}
    except Exception as exc:
        db.rollback()  # Cursor, transactions and balances must never diverge.
        db.refresh(connection)
        if isinstance(exc, PlaidError):
            connection.error_code = exc.code
            if exc.code in ("ITEM_LOGIN_REQUIRED", "ITEM_ACCESS_NOT_GRANTED", "ACCESS_NOT_GRANTED", "INVALID_ACCESS_TOKEN"):
                connection.status = "needs_login"
        connection.sync_lock_until = None
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        return {**public_connection(connection), "error": "Bank update failed. Saved data is still available; try again shortly."}


def disconnect(db, connection):
    now = utcnow()
    acquired = db.execute(update(BankConnection).where(BankConnection.id == connection.id,
        or_(BankConnection.sync_lock_until.is_(None), BankConnection.sync_lock_until < now))
        .values(sync_lock_until=now + timedelta(minutes=5)).execution_options(synchronize_session=False))
    db.commit()
    if acquired.rowcount != 1:
        raise HTTPException(409, "A bank update is running. Wait for it to finish, then disconnect.")
    db.refresh(connection)
    # Revoke provider access before erasing local credentials; failures remain retryable.
    try:
        plaid("item/remove", access_token=token(connection))
    except Exception as exc:
        if not isinstance(exc, PlaidError) or exc.code not in ("ITEM_NOT_FOUND", "INVALID_ACCESS_TOKEN"):
            connection.sync_lock_until = None
            db.commit()
            raise HTTPException(503, "Could not disconnect the bank. Try again before deleting its saved data.")
    db.execute(delete(Transaction).where(Transaction.bank_connection_id == connection.id))
    db.execute(delete(Account).where(Account.bank_connection_id == connection.id))
    db.delete(connection)
    db.commit()


def disconnect_all(db, user_id):
    for connection in db.scalars(select(BankConnection).where(BankConnection.user_id == user_id)).all():
        disconnect(db, connection)
