from sqlalchemy import Column, Integer, Text, Float, DateTime, Date, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    export_url = Column(Text)
    file_pattern = Column(Text)
    column_mapping = Column(JSON)
    importer_preset = Column(Text, default="generic")
    notes = Column(Text)

    accounts = relationship("Account", back_populates="institution")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    currency = Column(Text, default="USD")
    created_at = Column(DateTime, server_default=func.now())
    external_id = Column(Text)
    sync_source = Column(Text)
    source_kind = Column(Text)
    source_record_id = Column(Text)
    source_priority = Column(Integer, default=0)
    provenance = Column(JSON)
    merge_conflict = Column(Boolean, default=False)

    institution = relationship("Institution", back_populates="accounts")
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    balance_snapshots = relationship("BalanceSnapshot", back_populates="account", cascade="all, delete-orphan")
    real_estate = relationship("RealEstate", back_populates="account", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    cost_basis = Column(Float)
    last_price = Column(Float)
    last_updated = Column(DateTime)
    source = Column(Text, default="csv")

    account = relationship("Account", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    import_log_id = Column(Integer, ForeignKey("import_log.id"), nullable=True)
    date = Column(Date, nullable=False)
    type = Column(Text, nullable=False)
    symbol = Column(Text)
    quantity = Column(Float)
    price = Column(Float)
    amount = Column(Float)
    description = Column(Text)
    raw_row = Column(JSON)
    import_hash = Column(Text, unique=True)
    external_id = Column(Text)
    sync_source = Column(Text)
    source_kind = Column(Text)
    source_record_id = Column(Text)
    source_priority = Column(Integer, default=0)
    canonical_key = Column(Text)
    provenance = Column(JSON)
    merge_conflict = Column(Boolean, default=False)

    account = relationship("Account", back_populates="transactions")


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    balance = Column(Float, nullable=False)

    account = relationship("Account", back_populates="balance_snapshots")


class RealEstate(Base):
    __tablename__ = "real_estate"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    address = Column(Text, nullable=False)
    purchase_price = Column(Float)
    purchase_date = Column(Date)
    zillow_estimate = Column(Float)
    manual_override = Column(Float)
    mortgage_balance = Column(Float)
    mortgage_rate = Column(Float)  # APR percentage, e.g. 6.75
    last_updated = Column(DateTime)

    account = relationship("Account", back_populates="real_estate")

    @property
    def effective_value(self):
        return self.manual_override if self.manual_override is not None else self.zillow_estimate


class ImportLog(Base):
    __tablename__ = "import_log"

    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=False)
    filepath = Column(Text)
    institution_name = Column(Text)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    preset_used = Column(Text)
    rows_imported = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    status = Column(Text, default="success")  # success | error | skipped
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    rows_failed = Column(Integer, default=0)
    parse_errors = Column(Text)
    potential_transfers = Column(Integer, default=0)
    header_drift = Column(JSON)
    header_drift_detected = Column(Boolean, default=False)
    header_drift_added = Column(JSON)
    header_drift_removed = Column(JSON)
    header_drift_order_changed = Column(Boolean, default=False)

    account = relationship("Account")


class DebtDetail(Base):
    __tablename__ = "debt_details"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=False)
    interest_rate = Column(Float, default=0.0)   # APR as percent, e.g. 22.99
    minimum_payment = Column(Float, default=0.0)
    payoff_date = Column(Date, nullable=True)

    account = relationship("Account")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(Text, primary_key=True)
    value = Column(Text)


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=False)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class NewsCache(Base):
    __tablename__ = "news_cache"

    id = Column(Integer, primary_key=True)
    source = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, server_default=func.now())
    summary = Column(Text)
    category = Column(Text)


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id = Column(Integer, primary_key=True)
    provider = Column(Text, nullable=False)  # plaid | sheets
    name = Column(Text, nullable=False)
    status = Column(Text, default="active")  # active | disabled | error | relink_required
    config_json = Column(JSON)
    encrypted_secret = Column(Text)
    external_item_id = Column(Text)
    cursor = Column(Text)
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IntegrationRun(Base):
    __tablename__ = "integration_runs"

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("integration_connections.id"), nullable=False)
    trigger = Column(Text, nullable=False)  # manual | scheduled | startup
    status = Column(Text, default="running")  # running | success | error
    details = Column(JSON)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime)

    connection = relationship("IntegrationConnection")
