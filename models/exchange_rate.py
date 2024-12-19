from sqlalchemy import Column, Date, Float, Index, String

from database import Base


class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'
    __table_args__ = (
        # One row per currency and ECB publication day. Rows imported before the
        # column existed keep NULL here, and SQLite treats NULLs as distinct.
        Index('ux_exchange_rate_currency_published_on', 'currency', 'published_on', unique=True),
    )

    currency = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    change = Column(Float, nullable=True)
    published_on = Column(Date, nullable=True, index=True)
