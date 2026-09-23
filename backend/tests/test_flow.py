import json


CSV = b"Date,Description,Amount\n2026-09-01,STARBUCKS,-4.50\n2026-09-02,Payroll,100.00\n2026-09-03,NETFLIX,-15.49\n"
MAPPING = {"date": "Date", "description": "Description", "amount": "Amount"}


def auth(client, email):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "strong-test-password"})
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_import_dashboard_and_user_isolation(client):
    alice = auth(client, "alice@example.com")
    bob = auth(client, "bob@example.com")
    preview = client.post("/api/v1/imports/preview", headers=alice, files={"file": ("bank.csv", CSV, "text/csv")})
    assert preview.status_code == 200
    assert preview.json()["row_count"] == 3
    result = client.post("/api/v1/imports/confirm", headers=alice, files={"file": ("bank.csv", CSV, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    assert result.status_code == 200, result.text
    assert result.json()["imported_count"] == 3
    duplicate = client.post("/api/v1/imports/confirm", headers=alice, files={"file": ("bank.csv", CSV, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    assert duplicate.json()["duplicate_count"] == 3
    summary = client.get("/api/v1/analytics/summary", headers=alice).json()["currencies"]["USD"]
    assert summary["income"] == "100.00"
    assert summary["spending"] == "19.99"
    assert summary["net"] == "80.01"
    assert client.get("/api/v1/transactions", headers=bob).json()["total"] == 0
    first = client.get("/api/v1/transactions", headers=alice).json()["items"][0]
    assert client.patch(f"/api/v1/transactions/{first['id']}", headers=bob, json={"category": "Shopping"}).status_code == 404
    assert client.delete(f"/api/v1/imports/{result.json()['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/v1/imports/{result.json()['id']}", headers=alice).status_code == 200
    assert client.get("/api/v1/transactions", headers=alice).json()["total"] == 0


def test_bad_row_and_category_preference(client):
    headers = auth(client, "category@example.com")
    data = b"Date,Description,Amount\n2026-09-01,New Shop,-8.00\nnot-a-date,Other,-4.00\n"
    result = client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    assert result.json()["imported_count"] == 1
    assert result.json()["rejected_count"] == 1
    item = client.get("/api/v1/transactions", headers=headers).json()["items"][0]
    changed = client.patch(f"/api/v1/transactions/{item['id']}", headers=headers, json={"category": "Groceries"})
    assert changed.json()["category_source"] == "user"
    data2 = b"Date,Description,Amount\n2026-09-04,New Shop,-9.00\n"
    client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data2, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    rows = client.get("/api/v1/transactions", headers=headers).json()["items"]
    assert rows[0]["category"] == "Groceries"
    assert rows[0]["category_source"] == "preference"


def test_ambiguous_date_rejected_until_format_selected(client):
    headers = auth(client, "date@example.com")
    data = b"Date,Description,Amount\n03/04/2026,Coffee,-2.00\n"
    response = client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    assert response.json()["rejected_count"] == 1
    mapped = dict(MAPPING, date_format="%m/%d/%Y")
    response = client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data, "text/csv")}, data={"mapping_json": json.dumps(mapped)})
    assert response.json()["imported_count"] == 1


def test_debit_credit_filters_export_and_deletion(client):
    headers = auth(client, "privacy@example.com")
    # Export must escape the formula prefix without changing a numeric signed amount.
    data = b"Date,Description,Debit,Credit\n2026-09-01,=EVIL,10.00,\n2026-09-02,Salary,,250.00\n2026-09-03,Transfer to savings,50.00,\n"
    mapping = {"date": "Date", "description": "Description", "debit": "Debit", "credit": "Credit"}
    result = client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data, "text/csv")}, data={"mapping_json": json.dumps(mapping)})
    assert result.json()["imported_count"] == 3
    summary = client.get("/api/v1/analytics/summary", headers=headers).json()["currencies"]["USD"]
    assert summary["income"] == "250.00"
    assert summary["spending"] == "10.00"
    filtered = client.get("/api/v1/transactions?min_amount=40&direction=expense", headers=headers).json()
    assert filtered["total"] == 1
    export = client.get("/api/v1/export/transactions", headers=headers)
    assert "'=EVIL" in export.text
    assert "-10.00" in export.text
    assert client.delete("/api/v1/data", headers=headers).json()["deleted"]
    assert client.get("/api/v1/transactions", headers=headers).json()["total"] == 0
    assert client.delete("/api/v1/me", headers=headers).json()["deleted"]
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_refund_pair_and_review_filter(client):
    headers = auth(client, "refund@example.com")
    data = b"Date,Description,Amount\n2026-09-01,Unknown Store,-20.00\n2026-09-05,Unknown Store,20.00\n"
    result = client.post("/api/v1/imports/confirm", headers=headers, files={"file": ("bank.csv", data, "text/csv")}, data={"mapping_json": json.dumps(MAPPING)})
    assert result.json()["imported_count"] == 2
    rows = client.get("/api/v1/transactions", headers=headers).json()["items"]
    assert rows[0]["is_refund"] is True
    summary = client.get("/api/v1/analytics/summary", headers=headers).json()["currencies"]["USD"]
    assert summary["refunds"] == "20.00"
    assert summary["income"] == "0.00"
    assert client.get("/api/v1/transactions?needs_review=true", headers=headers).json()["total"] == 2
    html = client.post("/api/v1/imports/preview", headers=headers, files={"file": ("fake.csv", b"<html>not a csv</html>", "text/csv")})
    assert html.status_code == 400


def test_saved_mapping_reused_only_for_owner(client):
    alice = auth(client, "profile-alice@example.com")
    bob = auth(client, "profile-bob@example.com")
    result = client.post("/api/v1/imports/confirm", headers=alice, files={"file": ("bank.csv", CSV, "text/csv")}, data={"mapping_json": json.dumps(MAPPING), "profile_name": "My bank"})
    assert result.status_code == 200
    preview = client.post("/api/v1/imports/preview", headers=alice, files={"file": ("bank.csv", CSV, "text/csv")}).json()
    assert preview["saved_profile"] == "My bank"
    assert preview["suggested_mapping"]["amount"] == "Amount"
    assert client.get("/api/v1/import-profiles", headers=alice).json()[0]["name"] == "My bank"
    assert client.get("/api/v1/import-profiles", headers=bob).json() == []
    bob_preview = client.post("/api/v1/imports/preview", headers=bob, files={"file": ("bank.csv", CSV, "text/csv")}).json()
    assert bob_preview["saved_profile"] is None


def test_validation_error_names_field_without_echoing_input(client):
    response = client.post("/api/v1/auth/register", json={"email": "invalid-email", "password": "valid-password"})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Check: email"
    assert "invalid-email" not in response.text
