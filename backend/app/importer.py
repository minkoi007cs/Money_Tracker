import csv
import hashlib
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
CATEGORIES = [
    "Food & Dining", "Groceries", "Transportation", "Shopping", "Entertainment", "Housing",
    "Utilities", "Subscriptions", "Education", "Health", "Travel", "Personal Care",
    "Income", "Transfers", "Fees", "Cash", "Gifts & Donations", "Other",
]
ALIASES = {
    "date": ["date", "transaction date", "trans date", "posted date"],
    "description": ["description", "details", "memo", "transaction", "name"],
    "merchant": ["merchant", "payee"],
    "amount": ["amount", "transaction amount"],
    "debit": ["debit", "withdrawal", "money out"],
    "credit": ["credit", "deposit", "money in"],
    "currency": ["currency", "ccy"],
}
MERCHANT_RULES = {
    "STARBUCKS": ("Starbucks", "Food & Dining"),
    "CHIPOTLE": ("Chipotle", "Food & Dining"),
    "MCDONALD": ("McDonald's", "Food & Dining"),
    "TRADER JOE": ("Trader Joe's", "Groceries"),
    "WALMART": ("Walmart", "Groceries"),
    "UBER": ("Uber", "Transportation"),
    "LYFT": ("Lyft", "Transportation"),
    "NETFLIX": ("Netflix", "Subscriptions"),
    "SPOTIFY": ("Spotify", "Subscriptions"),
    "AMZN": ("Amazon", "Shopping"),
    "AMAZON": ("Amazon", "Shopping"),
    "TARGET": ("Target", "Shopping"),
}


def load_csv(data: bytes):
    if not data or len(data) > MAX_BYTES or b"\x00" in data:
        raise HTTPException(400, "CSV is empty, too large, or contains binary data")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must use UTF-8 encoding")
    if text.lstrip().lower().startswith(("<html", "<!doctype html", "<script")):
        raise HTTPException(400, "HTML is not a CSV statement")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    headers = reader.fieldnames or []
    if not headers or len(headers) > 50 or len(set(headers)) != len(headers):
        raise HTTPException(400, "CSV headers are missing, duplicated, or too numerous")
    rows = []
    for row in reader:
        if len(rows) >= MAX_ROWS:
            raise HTTPException(400, "CSV exceeds the row limit")
        rows.append(row)
    return headers, rows


def detect_mapping(headers):
    lowered = {h.strip().lower(): h for h in headers}
    result = {}
    for field, names in ALIASES.items():
        for name in names:
            if name in lowered:
                result[field] = lowered[name]
                break
    return result


def validate_mapping(mapping, headers):
    if not mapping.get("date") or not mapping.get("description"):
        raise HTTPException(400, "Map date and description columns")
    if not mapping.get("amount") and not (mapping.get("debit") or mapping.get("credit")):
        raise HTTPException(400, "Map amount or debit/credit columns")
    if any(mapping.get(key) not in headers for key in ALIASES if mapping.get(key)):
        raise HTTPException(400, "Mapping contains an unknown column")
    if mapping.get("amount") and (mapping.get("debit") or mapping.get("credit")):
        raise HTTPException(400, "Choose one amount convention")
    if mapping.get("date_format") not in (None, "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        raise HTTPException(400, "Unsupported date format")
    if mapping.get("sign_mode", "negative_spend") not in ("negative_spend", "positive_spend"):
        raise HTTPException(400, "Unsupported sign convention")


def parse_date(value, date_format=None):
    value = (value or "").strip()
    if not value:
        raise ValueError("Missing date")
    if date_format:
        return datetime.strptime(value, date_format).date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.strptime(value, "%Y-%m-%d").date()
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        if a <= 12 and b <= 12:
            raise ValueError("Ambiguous date; select a date format")
        fmt = "%m/%d/%Y" if a <= 12 else "%d/%m/%Y"
        return datetime.strptime(value, fmt).date()
    raise ValueError("Unsupported date")


def parse_money(value):
    raw = (value or "").strip()
    if not raw:
        return Decimal("0")
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()").replace(",", "").replace("$", "").replace("€", "").replace("£", "")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise ValueError("Invalid amount")
    if not amount.is_finite() or amount.as_tuple().exponent < -2 or abs(amount) > Decimal("9999999999999999.99"):
        raise ValueError("Amount precision or size is unsupported")
    return -amount if negative else amount


def normalize_description(value):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&'-]", " ", value.upper())).strip()


def merchant_and_category(raw, merchant_raw, amount):
    source = normalize_description(merchant_raw or raw)
    for needle, (merchant, category) in MERCHANT_RULES.items():
        if needle in source:
            return merchant, category, Decimal("0.95")
    merchant = re.sub(r"\b\d{3,}\b", "", source).strip()[:255] or "Unknown merchant"
    if amount > 0:
        return merchant.title(), "Income", Decimal("0.50")
    if "RENT" in source:
        return merchant.title(), "Housing", Decimal("0.75")
    if "GROCERY" in source or "MARKET" in source:
        return merchant.title(), "Groceries", Decimal("0.65")
    if "FEE" in source:
        return merchant.title(), "Fees", Decimal("0.70")
    return merchant.title(), "Other", Decimal("0.20")


def normalize_row(row, mapping, user_id, default_currency="USD"):
    if None in row:
        raise ValueError("Row has more columns than the header")
    date = parse_date(row.get(mapping["date"]), mapping.get("date_format"))
    raw = (row.get(mapping["description"]) or "").strip()
    if not raw:
        raise ValueError("Missing description")
    if mapping.get("amount"):
        amount = parse_money(row.get(mapping["amount"]))
        if mapping.get("sign_mode") == "positive_spend":
            amount = -amount
    else:
        debit = parse_money(row.get(mapping.get("debit"))) if mapping.get("debit") else Decimal("0")
        credit = parse_money(row.get(mapping.get("credit"))) if mapping.get("credit") else Decimal("0")
        if debit and credit:
            raise ValueError("Both debit and credit are populated")
        amount = abs(credit) - abs(debit)
    if not amount:
        raise ValueError("Amount is zero or missing")
    currency = (row.get(mapping.get("currency")) or default_currency).strip().upper() if mapping.get("currency") else default_currency
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Invalid currency")
    merchant, category, confidence = merchant_and_category(raw, row.get(mapping.get("merchant")) if mapping.get("merchant") else None, amount)
    normalized = normalize_description(raw)
    fingerprint = hashlib.sha256(f"{user_id}|{date}|{amount}|{currency}|{normalized}".encode()).hexdigest()
    return {
        "transaction_date": date, "description_raw": raw, "description_normalized": normalized,
        "merchant_name": merchant, "amount": amount, "currency": currency, "category": category,
        "confidence": confidence, "fingerprint": fingerprint, "category_source": "rule",
        "is_transfer": "TRANSFER" in normalized or "PAYMENT TO SAVINGS" in normalized,
        "is_refund": amount > 0 and ("REFUND" in normalized or "RETURN" in normalized),
        "is_subscription": category == "Subscriptions",
    }
