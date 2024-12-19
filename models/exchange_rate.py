from sqlalchemy import Column, Float, String

from database import Base


class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'

    currency = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    change = Column(Float, nullable=True)
