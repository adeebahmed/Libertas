from sqlalchemy import Column, Integer, Text, Float, DateTime, Date, ForeignKey, JSON
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

    account = relationship("Account", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(Text, nullable=False)
    symbol = Column(Text)
    quantity = Column(Float)
    price = Column(Float)
    amount = Column(Float)
    description = Column(Text)
    raw_row = Column(JSON)
    import_hash = Column(Text, unique=True)

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

    account = relationship("Account")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(Text, primary_key=True)
    value = Column(Text)
