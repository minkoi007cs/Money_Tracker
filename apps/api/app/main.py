import csv
import hashlib
import io
import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .analytics import compare_month, recurring_series, summarize
from .auth import create_token, current_user, hash_password, verify_password
from .db import get_db
from .importer import CATEGORIES, detect_mapping, load_csv, merchant_and_category, normalize_description, validate_mapping
from .models import Account, ImportBatch, ImportProfile, MerchantPreference, RecurringOverride, Transaction, User, UserSettings
from .services.import_service import header_hash, process_import


app = FastAPI(title="Where Did My Money Go? API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(HTTPException)
async def http_error(_, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_error(_, exc):
    fields = sorted({str(error["loc"][-1]) for error in exc.errors() if error.get("loc")})
    message = "Check: " + ", ".join(fields) if fields else "Check the submitted fields"
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": message}})


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class TransactionPatch(BaseModel):
    category: Optional[str] = None
    merchant_name: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    is_transfer: Optional[bool] = None
    is_refund: Optional[bool] = None
    is_subscription: Optional[bool] = None
    account_id: Optional[str] = None


class ManualTransaction(BaseModel):
    date: date
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal
    currency: Optional[str] = None
    account_id: Optional[str] = None
    category: Optional[str] = None
    is_transfer: bool = False
    notes: str = Field(default="", max_length=2000)


class OverridePatch(BaseModel):
    kind: str


class SettingsPatch(BaseModel):
    currency: Optional[str] = None
    timezone: Optional[str] = None


class AccountInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    opening_balance: Decimal = Decimal("0")


def validate_account_payload(payload: AccountInput):
    if payload.currency not in ("USD", "EUR", "GBP", "VND") or not payload.opening_balance.is_finite() or payload.opening_balance.as_tuple().exponent < -2 or abs(payload.opening_balance) > Decimal("9999999999999999.99"):
        raise HTTPException(400, "Invalid currency or opening balance")
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "Account name is required")
    return name


def public_transaction(t):
    return {
        "id": t.id, "date": t.transaction_date.isoformat(), "description_raw": t.description_raw,
        "description_normalized": t.description_normalized, "merchant": t.merchant_name,
        "amount": str(t.amount), "currency": t.currency, "category": t.category,
        "category_source": t.category_source, "confidence": str(t.confidence),
        "is_transfer": t.is_transfer, "is_refund": t.is_refund,
        "is_subscription": t.is_subscription, "notes": t.notes, "import_id": t.import_id, "account_id": t.account_id,
    }


def owned_transaction(db, user, transaction_id):
    t = db.scalar(select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id))
    if not t:
        raise HTTPException(404, "Transaction not found")
    return t


def all_transactions(db, user):
    return list(db.scalars(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.transaction_date.desc())))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: Credentials, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    db.commit()
    return {"access_token": create_token(user.id), "user": {"id": user.id, "email": user.email}}


@app.post("/api/v1/auth/login")
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_token(user.id), "user": {"id": user.id, "email": user.email}}


@app.get("/api/v1/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email}


@app.delete("/api/v1/me")
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(MerchantPreference).where(MerchantPreference.user_id == user.id))
    db.execute(delete(RecurringOverride).where(RecurringOverride.user_id == user.id))
    db.execute(delete(ImportProfile).where(ImportProfile.user_id == user.id))
    db.execute(delete(UserSettings).where(UserSettings.user_id == user.id))
    db.execute(delete(Account).where(Account.user_id == user.id))
    db.delete(user)
    db.commit()
    return {"deleted": True}


async def csv_data(file):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Choose a .csv file")
    data = await file.read(10 * 1024 * 1024 + 1)
    return data


@app.post("/api/v1/imports/preview")
async def preview(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    headers, rows = load_csv(await csv_data(file))
    saved = db.scalar(select(ImportProfile).where(ImportProfile.user_id == user.id, ImportProfile.headers_hash == header_hash(headers)))
    return {"headers": headers, "sample": rows[:10], "row_count": len(rows), "suggested_mapping": json.loads(saved.mapping_json) if saved else detect_mapping(headers), "saved_profile": saved.name if saved else None, "date_formats": ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]}


@app.post("/api/v1/imports/confirm")
async def confirm_import(
    file: UploadFile = File(...), mapping_json: str = Form(...), profile_name: str = Form(""), account_id: Optional[str] = Form(None),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    data = await csv_data(file)
    headers, rows = load_csv(data)
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "Mapping must be valid JSON")
    if not isinstance(mapping, dict):
        raise HTTPException(400, "Mapping must be an object")
    validate_mapping(mapping, headers)
    if account_id:
        account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user.id))
        if not account:
            raise HTTPException(404, "Account not found")
        mapping["account_id"] = account_id
        mapping["account_currency"] = account.currency
    return process_import(db, user.id, file.filename or "statement.csv", data, headers, rows, mapping, profile_name)


@app.get("/api/v1/accounts")
def accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned = db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.created_at)).all()
    result = []
    for account in owned:
        movement = db.scalar(select(func.sum(Transaction.amount)).where(Transaction.user_id == user.id, Transaction.account_id == account.id)) or Decimal("0")
        result.append({"id": account.id, "name": account.name, "currency": account.currency, "opening_balance": str(account.opening_balance), "balance": str(account.opening_balance + movement)})
    return result


@app.post("/api/v1/accounts", status_code=201)
def create_account(payload: AccountInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = validate_account_payload(payload)
    account = Account(user_id=user.id, name=name, currency=payload.currency, opening_balance=payload.opening_balance)
    db.add(account)
    db.commit()
    return {"id": account.id, "name": account.name, "currency": account.currency, "opening_balance": str(account.opening_balance), "balance": str(account.opening_balance)}


@app.patch("/api/v1/accounts/{account_id}")
def update_account(account_id: str, payload: AccountInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user.id))
    if not account:
        raise HTTPException(404, "Account not found")
    name = validate_account_payload(payload)
    if payload.currency != account.currency and db.scalar(select(Transaction.id).where(Transaction.user_id == user.id, Transaction.account_id == account.id).limit(1)):
        raise HTTPException(400, "Cannot change currency while the account has transactions")
    account.name = name
    account.currency = payload.currency
    account.opening_balance = payload.opening_balance
    db.commit()
    return {"id": account.id, "name": account.name, "currency": account.currency, "opening_balance": str(account.opening_balance)}


@app.delete("/api/v1/accounts/{account_id}")
def delete_account(account_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user.id))
    if not account:
        raise HTTPException(404, "Account not found")
    db.execute(Transaction.__table__.update().where(Transaction.user_id == user.id, Transaction.account_id == account.id).values(account_id=None))
    db.delete(account)
    db.commit()
    return {"deleted": True}


@app.get("/api/v1/imports")
def imports(user: User = Depends(current_user), db: Session = Depends(get_db)):
    batches = db.scalars(select(ImportBatch).where(ImportBatch.user_id == user.id).order_by(ImportBatch.created_at.desc())).all()
    return [{"id": b.id, "filename": b.filename, "row_count": b.row_count, "imported_count": b.imported_count, "duplicate_count": b.duplicate_count, "rejected_count": b.rejected_count, "created_at": b.created_at.isoformat()} for b in batches]


@app.get("/api/v1/import-profiles")
def import_profiles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    profiles = db.scalars(select(ImportProfile).where(ImportProfile.user_id == user.id).order_by(ImportProfile.created_at.desc())).all()
    return [{"id": p.id, "name": p.name, "mapping": json.loads(p.mapping_json)} for p in profiles]


@app.delete("/api/v1/import-profiles/{profile_id}")
def delete_import_profile(profile_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(ImportProfile).where(ImportProfile.id == profile_id, ImportProfile.user_id == user.id))
    if not profile:
        raise HTTPException(404, "Import profile not found")
    db.delete(profile)
    db.commit()
    return {"deleted": True}


@app.delete("/api/v1/imports/{batch_id}")
def delete_import(batch_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    batch = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.user_id == user.id))
    if not batch:
        raise HTTPException(404, "Import not found")
    db.delete(batch)
    db.commit()
    return {"deleted": True}


@app.get("/api/v1/categories")
def categories(user: User = Depends(current_user)):
    return CATEGORIES


@app.get("/api/v1/transactions")
def transactions(
    search: Optional[str] = None, category: Optional[str] = None, start: Optional[date] = None,
    end: Optional[date] = None, direction: Optional[str] = None, currency: Optional[str] = None,
    min_amount: Optional[Decimal] = None, max_amount: Optional[Decimal] = None,
    is_transfer: Optional[bool] = None, is_subscription: Optional[bool] = None, needs_review: bool = False,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    filters = [Transaction.user_id == user.id]
    if search:
        filters.append((Transaction.merchant_name.ilike(f"%{search}%")) | (Transaction.description_raw.ilike(f"%{search}%")))
    if category:
        filters.append(Transaction.category == category)
    if start:
        filters.append(Transaction.transaction_date >= start)
    if end:
        filters.append(Transaction.transaction_date <= end)
    if direction == "income":
        filters.append(Transaction.amount > 0)
    elif direction == "expense":
        filters.append(Transaction.amount < 0)
    if currency:
        filters.append(Transaction.currency == currency.upper())
    if min_amount is not None:
        filters.append(func.abs(Transaction.amount) >= min_amount)
    if max_amount is not None:
        filters.append(func.abs(Transaction.amount) <= max_amount)
    if is_transfer is not None:
        filters.append(Transaction.is_transfer == is_transfer)
    if is_subscription is not None:
        filters.append(Transaction.is_subscription == is_subscription)
    if needs_review:
        filters.append(Transaction.confidence < Decimal("0.60"))
        filters.append(Transaction.category_source == "rule")
    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters))
    items = db.scalars(select(Transaction).where(*filters).order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [public_transaction(t) for t in items], "total": total, "page": page, "page_size": page_size}


@app.post("/api/v1/transactions", status_code=201)
def create_transaction(payload: ManualTransaction, user: User = Depends(current_user), db: Session = Depends(get_db)):
    description = payload.description.strip()
    if not description:
        raise HTTPException(400, "Description is required")
    amount = payload.amount
    if not amount.is_finite() or amount == 0 or amount.as_tuple().exponent < -2 or abs(amount) > Decimal("9999999999999999.99"):
        raise HTTPException(400, "Amount must be nonzero, finite, and have at most two decimal places")
    settings = db.get(UserSettings, user.id)
    account = None
    if payload.account_id:
        account = db.scalar(select(Account).where(Account.id == payload.account_id, Account.user_id == user.id))
        if not account:
            raise HTTPException(404, "Account not found")
    currency = (payload.currency or (account.currency if account else settings.currency)).upper()
    if currency not in ("USD", "EUR", "GBP", "VND"):
        raise HTTPException(400, "Unsupported currency")
    if account and currency != account.currency:
        raise HTTPException(400, "Currency must match the selected account")
    if payload.category is not None and payload.category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    merchant, suggested_category, _ = merchant_and_category(description, None, amount)
    normalized = normalize_description(description)
    transaction = Transaction(
        user_id=user.id, import_id=None, account_id=account.id if account else None, transaction_date=payload.date,
        description_raw=description, description_normalized=normalized,
        merchant_name=merchant, amount=amount, currency=currency,
        category=payload.category or suggested_category, category_source="user",
        confidence=Decimal("1"), fingerprint=hashlib.sha256(os.urandom(32)).hexdigest(),
        is_transfer=payload.is_transfer, is_refund=False, is_subscription=False,
        notes=payload.notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return public_transaction(transaction)


@app.get("/api/v1/transactions/{transaction_id}")
def transaction_detail(transaction_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return public_transaction(owned_transaction(db, user, transaction_id))


@app.patch("/api/v1/transactions/{transaction_id}")
def update_transaction(transaction_id: str, payload: TransactionPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = owned_transaction(db, user, transaction_id)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for key, value in changes.items() if key != "account_id"):
        raise HTTPException(400, "Updated fields cannot be null")
    if "account_id" in changes and changes["account_id"] is not None:
        target = db.scalar(select(Account).where(Account.id == changes["account_id"], Account.user_id == user.id))
        if not target:
            raise HTTPException(404, "Account not found")
        if target.currency != t.currency:
            raise HTTPException(400, "Currency must match the selected account")
    chosen_category = changes.pop("category", None)
    for key, value in changes.items():
        if key == "merchant_name" and (not value or len(value) > 255):
            raise HTTPException(400, "Merchant name is required and must be under 256 characters")
        setattr(t, key, value)
    if chosen_category is not None:
        if chosen_category not in CATEGORIES:
            raise HTTPException(400, "Unknown category")
        t.category = chosen_category
        t.category_source = "user"
        t.confidence = Decimal("1")
        key = t.merchant_name.casefold()
        preference = db.scalar(select(MerchantPreference).where(MerchantPreference.user_id == user.id, MerchantPreference.merchant_key == key))
        if preference:
            preference.category = t.category
        else:
            db.add(MerchantPreference(user_id=user.id, merchant_key=key, category=t.category))
    db.commit()
    return public_transaction(t)


@app.delete("/api/v1/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_transaction(db, user, transaction_id))
    db.commit()
    return {"deleted": True}


@app.get("/api/v1/analytics/summary")
def analytics_summary(start: Optional[date] = None, end: Optional[date] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Transaction).where(Transaction.user_id == user.id)
    if start:
        query = query.where(Transaction.transaction_date >= start)
    if end:
        query = query.where(Transaction.transaction_date <= end)
    return {"start": start, "end": end, "currencies": summarize(db.scalars(query).all())}


@app.get("/api/v1/analytics/comparison")
def analytics_comparison(user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, user.id)
    today = datetime.now(ZoneInfo(settings.timezone if settings else "UTC")).date()
    return compare_month(all_transactions(db, user), today)


@app.get("/api/v1/analytics/timeline")
def analytics_timeline(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {currency: summary["daily"] for currency, summary in summarize(all_transactions(db, user)).items()}


@app.get("/api/v1/recurring")
def recurring(user: User = Depends(current_user), db: Session = Depends(get_db)):
    overrides = {o.merchant_key: o.kind for o in db.scalars(select(RecurringOverride).where(RecurringOverride.user_id == user.id))}
    return recurring_series(all_transactions(db, user), overrides)


@app.get("/api/v1/subscriptions")
def subscriptions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    overrides = {o.merchant_key: o.kind for o in db.scalars(select(RecurringOverride).where(RecurringOverride.user_id == user.id))}
    return [item for item in recurring_series(all_transactions(db, user), overrides) if item["kind"] == "subscription"]


@app.patch("/api/v1/recurring/{merchant_key}")
def override_recurring(merchant_key: str, payload: OverridePatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if payload.kind not in ("subscription", "recurring_bill", "recurring_income", "ignored"):
        raise HTTPException(400, "Invalid recurring type")
    key = merchant_key.casefold()
    item = db.scalar(select(RecurringOverride).where(RecurringOverride.user_id == user.id, RecurringOverride.merchant_key == key))
    if item:
        item.kind = payload.kind
    else:
        db.add(RecurringOverride(user_id=user.id, merchant_key=key, kind=payload.kind))
    db.commit()
    return {"merchant_key": key, "kind": payload.kind}


@app.get("/api/v1/insights")
def insights(user: User = Depends(current_user), db: Session = Depends(get_db)):
    transactions = all_transactions(db, user)
    summary = summarize(transactions)
    items = []
    for currency, data in summary.items():
        if data["categories"]:
            top = data["categories"][0]
            items.append({"text": f"{top['name']} was your largest spending category: {top['amount']} {currency}.", "kind": "fact", "evidence": {"category": top["name"], "amount": top["amount"], "currency": currency}})
        if data["merchants"]:
            top = data["merchants"][0]
            items.append({"text": f"You spent {top['amount']} {currency} at {top['name']}.", "kind": "fact", "evidence": {"merchant": top["name"], "amount": top["amount"], "currency": currency}})
    for currency in summary:
        expenses = [t for t in transactions if t.currency == currency and t.amount < 0 and not t.is_transfer]
        if len(expenses) < 10:
            continue
        amounts = sorted(-t.amount for t in expenses)
        typical = amounts[len(amounts) // 2]
        unusual = max(expenses, key=lambda t: -t.amount)
        if typical > 0 and -unusual.amount >= typical * 3:
            items.append({"text": f"A {str(-unusual.amount)} {currency} transaction at {unusual.merchant_name} was higher than your typical purchase.", "kind": "estimate", "evidence": {"transaction_id": unusual.id, "amount": str(-unusual.amount), "median_purchase": str(typical), "currency": currency}})
    return items


def safe_csv_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


@app.get("/api/v1/export/transactions")
def export_transactions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Merchant", "Description", "Category", "Amount", "Currency", "Recurring", "Transfer", "Notes"])
    for t in all_transactions(db, user):
        writer.writerow([safe_csv_cell(t.transaction_date), safe_csv_cell(t.merchant_name), safe_csv_cell(t.description_raw), safe_csv_cell(t.category), str(t.amount), t.currency, t.is_subscription, t.is_transfer, safe_csv_cell(t.notes)])
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="transactions.csv"'})


@app.get("/api/v1/export/accounts")
def export_accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Account", "Currency", "Starting balance", "Current balance"])
    for account in accounts(user, db):
        writer.writerow([safe_csv_cell(account["name"]), account["currency"], account["opening_balance"], account["balance"]])
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="accounts.csv"'})


@app.delete("/api/v1/data")
def delete_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    db.execute(delete(ImportBatch).where(ImportBatch.user_id == user.id))
    db.execute(delete(MerchantPreference).where(MerchantPreference.user_id == user.id))
    db.execute(delete(RecurringOverride).where(RecurringOverride.user_id == user.id))
    db.execute(delete(ImportProfile).where(ImportProfile.user_id == user.id))
    db.execute(delete(Account).where(Account.user_id == user.id))
    db.commit()
    return {"deleted": True}


@app.get("/api/v1/settings")
def get_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, user.id)
    return {"currency": settings.currency, "timezone": settings.timezone}


@app.patch("/api/v1/settings")
def update_settings(payload: SettingsPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, user.id)
    if payload.currency is not None:
        if payload.currency not in ("USD", "EUR", "GBP", "VND"):
            raise HTTPException(400, "Unsupported currency")
        settings.currency = payload.currency
    if payload.timezone is not None:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(payload.timezone)
        except ZoneInfoNotFoundError:
            raise HTTPException(400, "Unknown timezone")
        settings.timezone = payload.timezone
    db.commit()
    return {"currency": settings.currency, "timezone": settings.timezone}
