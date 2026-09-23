"""Persist a confirmed CSV import within one database transaction."""

import hashlib
import json
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importer import normalize_row
from app.models import ImportBatch, ImportProfile, MerchantPreference, Transaction, UserSettings


def header_hash(headers):
    return hashlib.sha256(json.dumps(headers, ensure_ascii=False).encode()).hexdigest()


def process_import(db: Session, user_id: str, filename: str, data: bytes, headers, rows, mapping, profile_name=""):
    if profile_name:
        if len(profile_name) > 100:
            raise HTTPException(400, "Profile name is too long")
        signature = header_hash(headers)
        profile = db.scalar(select(ImportProfile).where(ImportProfile.user_id == user_id, ImportProfile.headers_hash == signature))
        if profile:
            profile.name = profile_name
            profile.mapping_json = json.dumps(mapping)
        else:
            db.add(ImportProfile(user_id=user_id, name=profile_name, headers_hash=signature, mapping_json=json.dumps(mapping)))
    settings = db.get(UserSettings, user_id)
    batch = ImportBatch(user_id=user_id, filename=filename[:255], file_hash=hashlib.sha256(data).hexdigest(), row_count=len(rows))
    db.add(batch)
    db.flush()
    seen = set(db.scalars(select(Transaction.fingerprint).where(Transaction.user_id == user_id)))
    in_batch_expenses = defaultdict(list)
    errors = []
    for number, row in enumerate(rows, start=2):
        try:
            values = normalize_row(row, mapping, user_id, settings.currency if settings else "USD")
        except (ValueError, KeyError, TypeError) as exc:
            batch.rejected_count += 1
            if len(errors) < 10:
                errors.append({"row": number, "reason": str(exc)})
            continue
        fingerprint = values["fingerprint"]
        if fingerprint in seen:
            batch.duplicate_count += 1
            continue
        seen.add(fingerprint)
        preference = db.scalar(select(MerchantPreference).where(MerchantPreference.user_id == user_id, MerchantPreference.merchant_key == values["merchant_name"].casefold()))
        if preference:
            values["category"] = preference.category
            values["category_source"] = "preference"
            values["confidence"] = Decimal("1")
        if values["amount"] > 0 and not values["is_refund"]:
            prior = db.scalar(select(Transaction.id).where(
                Transaction.user_id == user_id,
                Transaction.merchant_name == values["merchant_name"],
                Transaction.amount == -values["amount"],
                Transaction.transaction_date <= values["transaction_date"],
                Transaction.transaction_date >= values["transaction_date"] - timedelta(days=90),
            ).limit(1))
            dates = in_batch_expenses[(values["merchant_name"], -values["amount"])]
            within_batch = any(0 <= (values["transaction_date"] - when).days <= 90 for when in dates)
            if prior or within_batch:
                values["is_refund"] = True
        if values["amount"] < 0:
            in_batch_expenses[(values["merchant_name"], values["amount"])].append(values["transaction_date"])
        db.add(Transaction(user_id=user_id, import_id=batch.id, **values))
        batch.imported_count += 1
    db.commit()
    return {"id": batch.id, "row_count": batch.row_count, "imported_count": batch.imported_count, "duplicate_count": batch.duplicate_count, "rejected_count": batch.rejected_count, "errors": errors}
