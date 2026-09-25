from collections import defaultdict
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from statistics import median


def money(value):
    return str(value.quantize(Decimal("0.01")))


def next_occurrence(last, frequency):
    if frequency in ("Weekly", "Biweekly"):
        return last + timedelta(days=7 if frequency == "Weekly" else 14)
    months = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}[frequency]
    month_index = last.month - 1 + months
    year = last.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(last.day, monthrange(year, month)[1]))


def summarize(transactions):
    by_currency = defaultdict(lambda: {"income": Decimal("0"), "spending": Decimal("0"), "refunds": Decimal("0"), "net": Decimal("0"), "categories": defaultdict(Decimal), "merchants": defaultdict(Decimal), "daily": defaultdict(Decimal), "count": 0})
    for t in transactions:
        bucket = by_currency[t.currency]
        bucket["count"] += 1
        if t.is_transfer:
            continue
        bucket["net"] += t.amount
        if t.is_refund:
            bucket["refunds"] += t.amount
        elif t.amount > 0:
            bucket["income"] += t.amount
        else:
            spend = -t.amount
            bucket["spending"] += spend
            bucket["categories"][t.category] += spend
            bucket["merchants"][t.merchant_name] += spend
            bucket["daily"][t.transaction_date.isoformat()] += spend
    result = {}
    for currency, b in by_currency.items():
        result[currency] = {
            "income": money(b["income"]), "spending": money(b["spending"]),
            "refunds": money(b["refunds"]), "net": money(b["net"]), "count": b["count"],
            "categories": sorted([{"name": k, "amount": money(v)} for k, v in b["categories"].items()], key=lambda x: Decimal(x["amount"]), reverse=True),
            "merchants": sorted([{"name": k, "amount": money(v)} for k, v in b["merchants"].items()], key=lambda x: Decimal(x["amount"]), reverse=True)[:10],
            "daily": [{"date": k, "amount": money(v)} for k, v in sorted(b["daily"].items())],
        }
    return result


def recurring_series(transactions, overrides=None):
    overrides = overrides or {}
    grouped = defaultdict(list)
    for t in transactions:
        if t.is_transfer or t.is_refund:
            continue
        grouped[(t.merchant_name.casefold(), t.currency, 1 if t.amount > 0 else -1)].append(t)
    result = []
    for (key, currency, direction), items in grouped.items():
        items.sort(key=lambda t: t.transaction_date)
        if len(items) < 3:
            continue
        if direction < 0 and not any(t.is_subscription or t.category in ("Subscriptions", "Housing", "Utilities", "Fees") for t in items):
            continue
        gaps = [(b.transaction_date - a.transaction_date).days for a, b in zip(items, items[1:])]
        gap = median(gaps)
        periods = [(7, "Weekly", 2), (14, "Biweekly", 3), (30, "Monthly", 5), (91, "Quarterly", 10), (365, "Yearly", 20)]
        match = next(((days, name) for days, name, tolerance in periods if all(abs(g - days) <= tolerance for g in gaps)), None)
        if not match:
            continue
        amounts = [abs(t.amount) for t in items]
        average = sum(amounts, Decimal("0")) / len(amounts)
        if average == 0 or max(abs(v - average) for v in amounts) > max(Decimal("2"), average * Decimal("0.25")):
            continue
        kind = "recurring_income" if direction > 0 else "subscription" if any(t.is_subscription or t.category == "Subscriptions" for t in items) else "recurring_bill"
        kind = overrides.get(key, kind)
        if kind == "ignored":
            continue
        confidence = min(Decimal("0.99"), Decimal("0.60") + Decimal("0.10") * (len(items) - 3) + Decimal("0.20") * (1 - Decimal(str(max(abs(g - match[0]) for g in gaps))) / Decimal(max(1, match[0]))))
        result.append({
            "merchant_key": key, "merchant": items[-1].merchant_name, "currency": currency,
            "average_amount": money(average), "frequency": match[1], "kind": kind,
            "last_charged": items[-1].transaction_date.isoformat(),
            "next_expected_date": next_occurrence(items[-1].transaction_date, match[1]).isoformat(),
            "confidence": str(confidence.quantize(Decimal("0.01"))), "occurrences": len(items),
        })
    return sorted(result, key=lambda x: (x["next_expected_date"], x["merchant"]))


def compare_month(transactions, today=None):
    today = today or date.today()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    current = summarize([t for t in transactions if current_start <= t.transaction_date <= today])
    previous = summarize([t for t in transactions if previous_start <= t.transaction_date <= previous_end])
    currencies = set(current) | set(previous)
    result = {}
    for currency in currencies:
        cur = Decimal(current.get(currency, {}).get("spending", "0"))
        prev = Decimal(previous.get(currency, {}).get("spending", "0"))
        cur_categories = {x["name"]: Decimal(x["amount"]) for x in current.get(currency, {}).get("categories", [])}
        prev_categories = {x["name"]: Decimal(x["amount"]) for x in previous.get(currency, {}).get("categories", [])}
        categories = [{"name": name, "current": money(cur_categories.get(name, Decimal("0"))), "previous": money(prev_categories.get(name, Decimal("0"))), "difference": money(cur_categories.get(name, Decimal("0")) - prev_categories.get(name, Decimal("0")))} for name in sorted(cur_categories.keys() | prev_categories.keys())]
        result[currency] = {"current": money(cur), "previous": money(prev), "difference": money(cur - prev), "percent": str(((cur - prev) / prev * 100).quantize(Decimal("0.1"))) if prev else None, "categories": categories}
    return {"current_period": current_start.isoformat(), "previous_period": previous_start.isoformat(), "currencies": result, "note": "Current month is partial"}
