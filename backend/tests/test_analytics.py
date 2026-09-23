from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.analytics import compare_month, next_occurrence, recurring_series, summarize


def transaction(day, merchant, amount, category="Subscriptions", currency="USD", **flags):
    return SimpleNamespace(transaction_date=date.fromisoformat(day), merchant_name=merchant, amount=Decimal(amount), category=category, currency=currency, is_transfer=flags.get("is_transfer", False), is_refund=flags.get("is_refund", False), is_subscription=flags.get("is_subscription", False))


def test_recurring_classification_and_override():
    rows = [transaction(f"2026-{month:02d}-05", "Spotify", "-10.99") for month in (6, 7, 8, 9)]
    result = recurring_series(rows)
    assert result[0]["frequency"] == "Monthly"
    assert result[0]["kind"] == "subscription"
    assert result[0]["next_expected_date"] == "2026-10-05"
    assert recurring_series(rows, {"spotify": "ignored"}) == []
    groceries = [transaction(f"2026-{month:02d}-10", "Supermarket", "-50.00", "Groceries") for month in (6, 7, 8, 9)]
    assert recurring_series(groceries) == []


def test_comparison_is_decimal_and_currency_separated():
    rows = [
        transaction("2026-08-01", "Shop", "-10.00", "Shopping"),
        transaction("2026-09-01", "Shop", "-12.00", "Shopping"),
        transaction("2026-09-02", "Shop", "-5.00", "Shopping", currency="EUR"),
    ]
    summary = summarize(rows)
    assert summary["USD"]["spending"] == "22.00"
    assert summary["EUR"]["spending"] == "5.00"
    comparison = compare_month(rows, date(2026, 9, 23))["currencies"]
    assert comparison["USD"]["difference"] == "2.00"
    assert comparison["USD"]["categories"][0]["name"] == "Shopping"
    assert comparison["EUR"]["previous"] == "0.00"


def test_monthly_estimate_uses_calendar_day():
    assert next_occurrence(date(2026, 1, 31), "Monthly") == date(2026, 2, 28)
    assert next_occurrence(date(2026, 9, 5), "Monthly") == date(2026, 10, 5)
