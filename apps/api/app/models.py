import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    imports = relationship("ImportBatch", cascade="all, delete-orphan", back_populates="user")
    transactions = relationship("Transaction", cascade="all, delete-orphan", back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")


class BankConnection(Base):
    __tablename__ = "bank_connections"
    __table_args__ = (UniqueConstraint("user_id", "institution_id", "environment", name="uq_bank_user_institution_environment"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(String(255), unique=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(20))
    institution_name: Mapped[str] = mapped_column(String(100))
    institution_id: Mapped[str] = mapped_column(String(100))
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="connected")
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    history_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_lock_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    bank_connection_id: Mapped[str | None] = mapped_column(ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True, nullable=True)
    external_account_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mask: Mapped[str | None] = mapped_column(String(10), nullable=True)
    bank_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    available_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user = relationship("User", back_populates="imports")
    transactions = relationship("Transaction", cascade="all, delete-orphan", back_populates="import_batch")


class ImportProfile(Base):
    __tablename__ = "import_profiles"
    __table_args__ = (UniqueConstraint("user_id", "headers_hash", name="uq_profile_user_headers"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    headers_hash: Mapped[str] = mapped_column(String(64))
    mapping_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint", name="uq_user_fingerprint"),
        Index("ix_transaction_user_date", "user_id", "transaction_date"),
        Index("ix_transaction_user_merchant", "user_id", "merchant_name"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    import_id: Mapped[str | None] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), index=True, nullable=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), index=True, nullable=True)
    bank_connection_id: Mapped[str | None] = mapped_column(ForeignKey("bank_connections.id", ondelete="SET NULL"), index=True, nullable=True)
    external_transaction_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    pending: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    bank_overrides: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    transaction_date: Mapped[date] = mapped_column(Date)
    description_raw: Mapped[str] = mapped_column(Text)
    description_normalized: Mapped[str] = mapped_column(Text)
    merchant_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    category: Mapped[str] = mapped_column(String(100), default="Other")
    category_source: Mapped[str] = mapped_column(String(20), default="rule")
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    fingerprint: Mapped[str] = mapped_column(String(64))
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user = relationship("User", back_populates="transactions")
    import_batch = relationship("ImportBatch", back_populates="transactions")


class MerchantPreference(Base):
    __tablename__ = "merchant_category_preferences"
    __table_args__ = (UniqueConstraint("user_id", "merchant_key", name="uq_preference_user_merchant"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    merchant_key: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))


class RecurringOverride(Base):
    __tablename__ = "recurring_overrides"
    __table_args__ = (UniqueConstraint("user_id", "merchant_key", name="uq_override_user_merchant"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    merchant_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(30))
