import math
import re
from datetime import date
from typing import NamedTuple
from xml.etree import ElementTree as ET

import requests
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import SessionLocal
from models.exchange_rate import ExchangeRate
from .constants import ECB_API_URL

MAX_FEED_BYTES = 2 * 1024 * 1024
# ECB rates carry at most five decimals; rounding the stored difference keeps
# float subtraction noise (0.0075000000000000622) out of the API.
CHANGE_DECIMALS = 6


class FeedSnapshot(NamedTuple):
    published_on: date
    rates: dict


def validate_rates(rates):
    if not rates:
        raise ValueError('No exchange rates received')
    for currency, value in rates.items():
        if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
            raise ValueError('Invalid currency code')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Rates must be finite positive numbers')


def fetch_and_store_exchange_rates():
    snapshot = fetch_exchange_rates()
    with SessionLocal() as session:
        inserted = insert_into_db(session, snapshot.rates, snapshot.published_on)
    return snapshot.published_on, inserted


def fetch_exchange_rates() -> FeedSnapshot:
    parts = []
    size = 0
    with requests.get(ECB_API_URL, timeout=15, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(32 * 1024):
            size += len(chunk)
            if size > MAX_FEED_BYTES:
                raise ValueError('ECB response exceeds limit')
            parts.append(chunk)
    return parse_feed(b''.join(parts))


def parse_feed(content: bytes) -> FeedSnapshot:
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise ValueError('DTD/entity declarations are not supported')
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError('ECB response is not well-formed XML') from exc
    days = root.findall('.//{*}Cube[@time]')
    if len(days) != 1:
        raise ValueError('Expected exactly one publication day in the daily feed')
    try:
        published_on = date.fromisoformat(days[0].attrib['time'])
    except ValueError as exc:
        raise ValueError('Invalid publication date in ECB response') from exc
    rates = {}
    for currency in days[0].findall('.//{*}Cube[@currency]'):
        code = currency.attrib['currency']
        if code in rates:
            raise ValueError('Duplicate currency in ECB response')
        try:
            rates[code] = float(currency.attrib['rate'])
        except KeyError as exc:
            raise ValueError(f'Missing rate for {code}') from exc
    validate_rates(rates)
    return FeedSnapshot(published_on, rates)


def insert_into_db(db: Session, rates: dict, published_on: date | None = None) -> int:
    '''Store one batch and return how many rows were added.

    When ``published_on`` is given, currencies already stored for that ECB
    publication day are skipped, so re-running an import is a no-op.
    '''
    validate_rates(rates)
    already_stored = set()
    if published_on is not None:
        already_stored = {
            currency for (currency,) in
            db.query(ExchangeRate.currency).filter(ExchangeRate.published_on == published_on)
        }
    inserted = 0
    try:
        for currency, rate in rates.items():
            if currency in already_stored:
                continue
            previous = (
                db.query(ExchangeRate)
                .filter_by(currency=currency)
                .order_by(desc(ExchangeRate.created_at), desc(ExchangeRate.id))
                .first()
            )
            change = round(rate - previous.rate, CHANGE_DECIMALS) if previous else None
            db.add(ExchangeRate(currency=currency, rate=rate, change=change, published_on=published_on))
            inserted += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return inserted
