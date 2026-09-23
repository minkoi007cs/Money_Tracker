"""Create an explicitly synthetic local demo workspace.

Run from backend/: DEMO_PASSWORD=your-local-password ../.venv/bin/python scripts/seed_demo.py
"""
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal
from app.importer import normalize_row
from app.models import ImportBatch, Transaction, User, UserSettings


def main():
    if os.getenv("APP_ENV") == "production":
        raise SystemExit("Demo seeding is disabled in production")
    password = os.getenv("DEMO_PASSWORD")
    if not password or len(password) < 10:
        raise SystemExit("Set DEMO_PASSWORD to at least 10 characters")
    email = "demo@example.com"
    mapping = {"date": "Date", "description": "Description", "merchant": "Merchant", "amount": "Amount", "date_format": "%Y-%m-%d"}
    monthly = [
        ("01", "Payroll", "Payroll", "2450.00"),
        ("02", "Apartment rent", "Apartment rent", "-600.00"),
        ("05", "Spotify", "Spotify", "-10.99"),
        ("07", "Netflix", "Netflix", "-15.49"),
        ("10", "Trader Joe's", "Trader Joe's", "-78.20"),
        ("12", "Starbucks", "Starbucks", "-6.80"),
        ("14", "Uber trip", "Uber", "-23.50"),
        ("16", "Amazon order", "Amazon", "-49.99"),
        ("18", "Chipotle", "Chipotle", "-14.75"),
        ("20", "Target", "Target", "-42.00"),
    ]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            db.add(UserSettings(user_id=user.id))
        if db.scalar(select(ImportBatch.id).where(ImportBatch.user_id == user.id, ImportBatch.filename == "synthetic-demo.csv")):
            print("Demo data already exists for demo@example.com")
            return
        batch = ImportBatch(user_id=user.id, filename="synthetic-demo.csv", file_hash=hashlib.sha256(b"SYNTHETIC DEMO DATA").hexdigest(), row_count=40)
        db.add(batch)
        db.flush()
        for month in (6, 7, 8, 9):
            for day, description, merchant, amount in monthly:
                row = {"Date": f"2026-{month:02d}-{day}", "Description": f"DEMO DATA - {description}", "Merchant": merchant, "Amount": amount}
                values = normalize_row(row, mapping, user.id)
                db.add(Transaction(user_id=user.id, import_id=batch.id, **values))
                batch.imported_count += 1
        db.commit()
    print("Created 40 synthetic transactions for demo@example.com")


if __name__ == "__main__":
    main()
