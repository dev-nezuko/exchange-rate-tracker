import datetime
import random

from sqlalchemy.orm import Session

from models import ExchangeRate


def test_create_exchange_rate(
    test_exchange_rate: ExchangeRate, test_db: Session
):
    test_db.add(test_exchange_rate)
    test_db.commit()
    test_db.refresh(test_exchange_rate)
    exchange_rate = (
        test_db.query(ExchangeRate)
        .filter_by(
            id=test_exchange_rate.id,
        )
        .first()
    )

    assert test_exchange_rate.id is not None
    assert test_exchange_rate.rate == exchange_rate.rate
    assert test_exchange_rate.change == exchange_rate.change


def test_create_exchange_rate_with_none_difference(test_db: Session):
    exchange_rate = ExchangeRate(currency='USD', rate=1.45, change=None)
    test_db.add(exchange_rate)
    test_db.commit()
    test_db.refresh(exchange_rate)

    assert exchange_rate.change is None
    assert exchange_rate.rate == 1.45
    assert exchange_rate.id is not None


def test_exchange_rate_timestamps(
    test_exchange_rate: ExchangeRate, test_db: Session
):
    test_db.add(test_exchange_rate)
    test_db.commit()
    test_db.refresh(test_exchange_rate)

    assert isinstance(test_exchange_rate.created_at, datetime.datetime)
    assert isinstance(test_exchange_rate.updated_at, datetime.datetime)
    assert test_exchange_rate.created_at == test_exchange_rate.updated_at


def test_update_exchange_rate(test_db: Session):
    exchange_rate = ExchangeRate(currency='USD', rate=1.30, change=0.02)
    test_db.add(exchange_rate)
    test_db.commit()
    test_db.refresh(exchange_rate)

    exchange_rate.rate = 1.40
    exchange_rate.change = 0.05
    test_db.commit()
    test_db.refresh(exchange_rate)

    assert exchange_rate.rate == 1.40
    assert exchange_rate.change == 0.05


def test_create_exchange_rate_random(test_db: Session):
    rate = round(random.uniform(1.0, 100.0), 2)
    difference = round(random.uniform(-10.0, 10.0), 2)
    exchange_rate = ExchangeRate(currency='USD', rate=rate, change=difference)

    test_db.add(exchange_rate)
    test_db.commit()
    test_db.refresh(exchange_rate)

    assert exchange_rate.rate == rate
    assert exchange_rate.change == difference
