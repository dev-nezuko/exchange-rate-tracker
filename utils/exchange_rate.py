import math
import re
from xml.etree import ElementTree as ET

import requests
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import SessionLocal
from models.exchange_rate import ExchangeRate
from .constants import ECB_API_URL


def validate_rates(rates):
    if not rates:
        raise ValueError('No exchange rates received')
    for currency, value in rates.items():
        if not isinstance(currency, str) or not re.fullmatch(r'[A-Z]{3}', currency):
            raise ValueError('Invalid currency code')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Rates must be finite positive numbers')


def fetch_and_store_exchange_rates():
    rates = fetch_exchange_rates()
    with SessionLocal() as session:
        insert_into_db(session, rates)


def fetch_exchange_rates():
    parts = []
    size = 0
    with requests.get(ECB_API_URL, timeout=15, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(32 * 1024):
            size += len(chunk)
            if size > 2 * 1024 * 1024:
                raise ValueError('ECB response exceeds limit')
            parts.append(chunk)
    content = b''.join(parts)
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise ValueError('DTD/entity declarations are not supported')
    root = ET.fromstring(content)
    rates = {}
    for cube in root.findall('.//{*}Cube[@time]'):
        for currency in cube.findall('.//{*}Cube[@currency]'):
            code = currency.attrib['currency']
            if code in rates:
                raise ValueError('Duplicate currency in ECB response')
            rates[code] = float(currency.attrib['rate'])
    validate_rates(rates)
    return rates


def insert_into_db(db: Session, rates: dict):
    validate_rates(rates)
    try:
        for currency, rate in rates.items():
            previous = db.query(ExchangeRate).filter_by(currency=currency).order_by(desc(ExchangeRate.created_at), desc(ExchangeRate.id)).first()
            change = rate - previous.rate if previous else None
            db.add(ExchangeRate(currency=currency, rate=rate, change=change))
        db.commit()
    except Exception:
        db.rollback()
        raise
