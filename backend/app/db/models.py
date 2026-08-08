"""SQLAlchemy ORM models for securities, daily prices, signals, and portfolio holdings.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint

from app.db.session import Base


class Security(Base):
    """A listed company / stock symbol on NEPSE."""

    __tablename__ = "securities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    sector = Column(String(100), default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyPrice(Base):
    """Daily OHLCV + turnover record for a single symbol."""

    __tablename__ = "daily_prices"

    __table_args__ = (
        Index('ix_daily_price_symbol_date', 'symbol', 'date'),
        UniqueConstraint('symbol', 'date', name='uq_daily_price_symbol_date'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    turnover = Column(Float)

    def to_dict(self) -> dict:
        """Serialize daily price to a plain dictionary."""
        return {
            "symbol": self.symbol,
            "date": self.date.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
        }


class Signal(Base):
    """A trading signal (BUY / SELL / HOLD) generated for a symbol."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(10), nullable=False)
    confidence = Column(Float)
    reason = Column(Text)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PortfolioHolding(Base):
    """A user-defined portfolio position for tracking purposes."""

    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    avg_cost = Column(Float, nullable=False)
    buy_date = Column(Date)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialize portfolio holding to a plain dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "buy_date": self.buy_date.isoformat() if self.buy_date else None,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat(),
        }


