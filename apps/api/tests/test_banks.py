"""Synthetic Plaid contract tests. No network or real bank credentials."""
import json
from datetime import timedelta
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from app.db import get_db
from app.main import app
from app.models import BankConnection, Transaction, utcnow
from app.services import bank_service as bank
from test_flow import auth, CSV, MAPPING


def page(added=None, modified=None, removed=None, cursor="c1", more=False):
    return dict(added=added or [], modified=modified or [], removed=removed or [], next_cursor=cursor,
                has_more=more, transactions_update_status="HISTORICAL_UPDATE_COMPLETE")


def txn(id="t1", amount=10, **kwargs):
    return dict(transaction_id=id, account_id="account-Chase", date="2026-10-19", name="Grocery", merchant_name="Shop",
        amount=amount, pending=False, iso_currency_code="USD", personal_finance_category={"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_GROCERIES"}) | kwargs


@pytest.fixture
def provider(monkeypatch):
    for key, value in {"PLAID_ENV": "sandbox", "PLAID_CLIENT_ID": "synthetic", "PLAID_SECRET": "synthetic",
        "BANK_TOKEN_ENCRYPTION_KEYS": Fernet.generate_key().decode(), "PLAID_REDIRECT_URI": "http://localhost:3000/banks/callback"}.items():
        monkeypatch.setenv(key, value)
    state = dict(calls=[], institution="Chase", pages=[], failure=None, item_error=None, remove_failure=False)
    def call(path, **payload):
        state["calls"].append((path, payload))
        name = state["institution"]
        if path == "link/token/create": return {"link_token": "link-synthetic"}
        if path == "item/public_token/exchange": return {"access_token": f"access-{name}", "item_id": f"item-{name}"}
        if path == "accounts/get":
            name = payload["access_token"].split("-")[-1]
            return {"item": {"institution_id": name, "institution_name": name}, "accounts": [dict(account_id=f"account-{name}", name="Checking", type="depository", mask="1234",
                balances=dict(current=1234.56, available=1200, iso_currency_code="USD"))]}
        if path == "transactions/sync":
            if state["failure"]: raise bank.PlaidError(state["failure"])
            result = state["pages"].pop(0) if state["pages"] else page()
            if isinstance(result, Exception): raise result
            return result
        if path == "item/remove":
            if state["remove_failure"]: raise bank.PlaidError("PROVIDER_UNAVAILABLE")
            return {"removed": True}
        if path == "item/get": return {"item": {"error": state["item_error"]}}
        raise AssertionError(path)
    monkeypatch.setattr(bank, "plaid", call)
    return state


def session():
    return next(app.dependency_overrides[get_db]())


def link(client, headers):
    r = client.post("/api/v1/banks/exchange", headers=headers, json={"public_token": "public-synthetic"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def reset(id):
    with session() as db:
        db.get(BankConnection, id).last_synced_at = None
        db.commit()


def sync(client, headers, id):
    return client.post(f"/api/v1/banks/{id}/sync", headers=headers)


def test_disabled(client, monkeypatch):
    monkeypatch.delenv("PLAID_SECRET", raising=False)
    h = auth(client, "disabled@example.com")
    assert not client.get("/api/v1/banks", headers=h).json()["configured"]
    assert client.post("/api/v1/banks/link-token", headers=h, json={}).status_code == 503
    assert client.get("/api/v1/banks").status_code == 401


def test_credentials_and_isolation(client, provider):
    a, b = auth(client, "alice@example.com"), auth(client, "bob@example.com")
    assert client.post("/api/v1/banks/link-token", headers=a, json={}).status_code == 200
    assert provider["calls"][-1][1]["products"] == ["transactions"]
    id = link(client, a)
    with session() as db:
        c = db.get(BankConnection, id)
        assert "access-Chase" not in c.access_token_encrypted
        assert bank.cipher().decrypt(c.access_token_encrypted.encode()).decode() == "access-Chase"
    listing = client.get("/api/v1/banks", headers=a)
    assert all(secret not in listing.text for secret in ["access-Chase", "item-Chase", "cursor"])
    assert client.get("/api/v1/banks", headers=b).json()["connections"] == []
    for suffix in ["sync", "reconnected"]:
        assert client.post(f"/api/v1/banks/{id}/{suffix}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/banks/{id}", headers=b).status_code == 404
    assert client.post("/api/v1/banks/exchange", headers=a, json={"public_token": "dup"}).status_code == 409
    assert not any(path == "item/remove" for path, _ in provider["calls"])


def test_balances_two_banks_pending_transfers_and_filters(client, provider):
    h = auth(client, "both@example.com")
    chase = link(client, h)
    provider["institution"] = "PNC"
    pnc = link(client, h)
    provider["pages"] = [page(added=[txn(), txn("pending", amount=9, pending=True), txn("payment", amount=200,
        personal_finance_category={"primary": "LOAN_PAYMENTS", "detailed": "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT"})])]
    assert sync(client, h, chase).status_code == 200
    provider["pages"] = [page(added=[txn("salary", amount=-100, account_id="account-PNC", personal_finance_category={"primary": "INCOME"})])]
    sync(client, h, pnc)
    accounts = client.get("/api/v1/accounts", headers=h).json()
    assert len(accounts) == 2 and all(a["balance"] == "1234.56" for a in accounts)
    assert all(a["available_balance"] == "1200.00" for a in accounts)
    id = accounts[0]["id"]
    assert client.get(f"/api/v1/transactions?account_id={id}", headers=h).json()["total"] == 3
    stats = client.get("/api/v1/analytics/summary", headers=h).json()["currencies"]["USD"]
    assert (stats["income"], stats["spending"], stats["net"], stats["count"]) == ("100.00", "10.00", "90.00", 3)
    assert client.get(f"/api/v1/analytics/summary?account_id={id}", headers=h).json()["currencies"]["USD"]["income"] == "0.00"
    assert client.post("/api/v1/transactions", headers=h, json={"date": "2026-10-19", "description": "manual", "amount": "-1", "account_id": id}).status_code == 400
    assert client.post("/api/v1/imports/confirm", headers=h, files={"file": ("bank.csv", CSV)}, data={"mapping_json": json.dumps(MAPPING), "account_id": id}).status_code == 400
    assert client.delete(f"/api/v1/accounts/{id}", headers=h).status_code == 400


def test_pending_posted_modifications_and_replay(client, provider):
    h = auth(client, "sync@example.com")
    id = link(client, h)
    provider["pages"] = [page(added=[txn("pending", pending=True)])]
    sync(client, h, id)
    pending = client.get("/api/v1/transactions", headers=h).json()["items"][0]
    client.patch(f"/api/v1/transactions/{pending['id']}", headers=h, json={"notes": "pending note", "category": "Shopping"})
    reset(id)
    provider["pages"] = [page(added=[txn("posted", amount=12, pending_transaction_id="pending")], removed=[{"transaction_id": "pending"}], cursor="c2")]
    sync(client, h, id)
    data = client.get("/api/v1/transactions", headers=h).json()
    assert data["total"] == 1 and data["items"][0]["amount"] == "-12.00" and not data["items"][0]["pending"]
    t = data["items"][0]
    assert t["notes"] == "pending note" and t["category"] == "Shopping"
    assert client.patch(f"/api/v1/transactions/{t['id']}", headers=h, json={"category": "Shopping", "notes": "keep", "is_transfer": True}).status_code == 200
    reset(id)
    provider["pages"] = [page(modified=[txn("posted", amount=13)], cursor="c3")]
    sync(client, h, id)
    t = client.get(f"/api/v1/transactions/{t['id']}", headers=h).json()
    assert (t["category"], t["category_source"], t["notes"], t["amount"], t["is_transfer"]) == ("Shopping", "user", "keep", "-13.00", True)
    assert client.delete(f"/api/v1/transactions/{t['id']}", headers=h).status_code == 400
    reset(id)
    provider["pages"] = [page(added=[txn("posted", amount=13)], cursor="c4")]
    sync(client, h, id)
    assert client.get("/api/v1/transactions", headers=h).json()["total"] == 1
    reset(id)
    provider["pages"] = [page(removed=[{"transaction_id": "posted"}], cursor="c5")]
    sync(client, h, id)
    assert client.get("/api/v1/transactions", headers=h).json()["total"] == 0


def test_pagination_restart_and_rollback(client, provider):
    h = auth(client, "pages@example.com")
    id = link(client, h)
    provider["pages"] = [page(added=[txn("discard")], cursor="bad", more=True), bank.PlaidError("TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION"),
        page(added=[txn("correct")], cursor="page1", more=True), page(added=[txn("correct2", amount=7)], cursor="done")]
    sync(client, h, id)
    assert [p.get("cursor") for path, p in provider["calls"] if path == "transactions/sync"] == [None, "bad", None, "page1"]
    assert client.get("/api/v1/transactions", headers=h).json()["total"] == 2
    reset(id)
    provider["pages"] = [page(added=[txn("valid"), txn("invalid", account_id="unknown")], cursor="never")]
    assert "error" in sync(client, h, id).json()
    with session() as db:
        assert db.get(BankConnection, id).cursor == "done"
        assert db.scalar(select(Transaction).where(Transaction.external_transaction_id == "valid")) is None
        assert db.get(BankConnection, id).sync_lock_until is None


def test_lease_cooldown_reauth_and_disconnect(client, provider):
    h = auth(client, "lifecycle@example.com")
    id = link(client, h)
    sync(client, h, id)
    assert sync(client, h, id).json()["skipped"]
    reset(id)
    with session() as db:
        db.get(BankConnection, id).sync_lock_until = utcnow() + timedelta(minutes=1)
        db.commit()
    assert sync(client, h, id).json()["skipped"]
    assert client.delete(f"/api/v1/banks/{id}", headers=h).status_code == 409
    with session() as db:
        db.get(BankConnection, id).sync_lock_until = None
        db.commit()
    provider["failure"] = "ITEM_LOGIN_REQUIRED"
    assert sync(client, h, id).json()["status"] == "needs_login"
    provider["item_error"] = {"error_code": "ITEM_LOGIN_REQUIRED"}
    assert client.post(f"/api/v1/banks/{id}/reconnected", headers=h).status_code == 409
    provider["item_error"] = None
    assert client.post(f"/api/v1/banks/{id}/reconnected", headers=h).status_code == 200
    provider["remove_failure"] = True
    assert client.delete(f"/api/v1/banks/{id}", headers=h).status_code == 503
    assert len(client.get("/api/v1/accounts", headers=h).json()) == 1
    provider["remove_failure"] = False
    assert client.delete(f"/api/v1/banks/{id}", headers=h).status_code == 200
    assert client.get("/api/v1/accounts", headers=h).json() == []


def test_environment_mismatch_keeps_data_and_unlocks(client, provider, monkeypatch):
    h = auth(client, "environment@example.com")
    id = link(client, h)
    monkeypatch.setenv("PLAID_ENV", "production")
    assert sync(client, h, id).status_code == 409
    with session() as db:
        assert db.get(BankConnection, id).sync_lock_until is None
    assert len(client.get("/api/v1/accounts", headers=h).json()) == 1


def test_delete_data_revokes_both_banks(client, provider):
    h = auth(client, "delete-banks@example.com")
    link(client, h)
    provider["institution"] = "PNC"
    link(client, h)
    assert client.delete("/api/v1/data", headers=h).status_code == 200
    assert len([p for path, p in provider["calls"] if path == "item/remove"]) == 2
    assert client.get("/api/v1/banks", headers=h).json()["connections"] == []
    assert client.get("/api/v1/accounts", headers=h).json() == []
    assert client.get("/api/v1/me", headers=h).status_code == 200


def test_null_balance_and_credit_balance_not_derived_from_transactions(client, provider):
    from app.models import Account
    h = auth(client, "credit@example.com")
    id = link(client, h)
    with session() as db:
        account = db.scalar(select(Account).where(Account.bank_connection_id == id))
        account.account_type = "credit"
        account.bank_balance = None
        account.available_balance = 900
        db.commit()
    result = client.get("/api/v1/accounts", headers=h).json()[0]
    assert result["balance"] is None and result["account_type"] == "credit"
    assert result["available_balance"] == "900.00"


def test_plaid_transport_uses_server_secrets_without_returning_them(client, monkeypatch):
    import httpx
    for key, value in {"PLAID_ENV": "sandbox", "PLAID_CLIENT_ID": "private-id", "PLAID_SECRET": "private-secret",
        "BANK_TOKEN_ENCRYPTION_KEYS": Fernet.generate_key().decode(), "PLAID_REDIRECT_URI": "http://localhost:3000/banks/callback"}.items():
        monkeypatch.setenv(key, value)
    def fake(url, **kwargs):
        assert url == "https://sandbox.plaid.com/link/token/create"
        assert kwargs["json"]["secret"] == "private-secret"
        return httpx.Response(400, json={"error_code": "INVALID_CONFIGURATION", "error_message": "private-secret private-id"})
    monkeypatch.setattr(bank.httpx, "post", fake)
    h = auth(client, "transport@example.com")
    response = client.post("/api/v1/banks/link-token", headers=h, json={})
    assert response.status_code == 503
    assert "private-secret" not in response.text and "private-id" not in response.text


def test_csv_cannot_inject_an_unvalidated_bank_or_another_users_account(client, provider):
    alice, bob = auth(client, "csv-alice@example.com"), auth(client, "csv-bob@example.com")
    link(client, alice)
    account = client.get("/api/v1/accounts", headers=alice).json()[0]
    injected = dict(MAPPING, account_id=account["id"], account_currency="USD")
    result = client.post("/api/v1/imports/confirm", headers=bob, files={"file": ("bank.csv", CSV)},
        data={"mapping_json": json.dumps(injected)})
    assert result.status_code == 200
    rows = client.get("/api/v1/transactions", headers=bob).json()["items"]
    assert rows and all(t["account_id"] is None for t in rows)
    assert client.get(f"/api/v1/transactions?account_id={account['id']}", headers=alice).json()["total"] == 0
