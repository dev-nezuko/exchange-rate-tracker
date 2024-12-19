from datetime import date

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from database import ensure_schema
from models import ExchangeRate
from utils import exchange_rate as importer

FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
    xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <Cube>
    <Cube time="2024-03-15">
      <Cube currency="USD" rate="1.0892"/>
      <Cube currency="JPY" rate="162.15"/>
    </Cube>
  </Cube>
</gesmes:Envelope>'''


def test_parse_feed_reads_the_publication_date_from_the_namespaced_feed():
    snapshot = importer.parse_feed(FEED)
    assert snapshot.published_on == date(2024, 3, 15)
    assert snapshot.rates == {'USD': 1.0892, 'JPY': 162.15}


@pytest.mark.parametrize('payload', [
    b'<Envelope><Cube><Cube time="15/03/2024"><Cube currency="USD" rate="1.1"/></Cube></Cube></Envelope>',
    b'<Envelope><Cube><Cube time="2024-03-14"><Cube currency="USD" rate="1.1"/></Cube>'
    b'<Cube time="2024-03-15"><Cube currency="USD" rate="1.2"/></Cube></Cube></Envelope>',
])
def test_parse_feed_rejects_bad_or_multiple_publication_days(payload):
    with pytest.raises(ValueError):
        importer.parse_feed(payload)


def test_insert_stores_publication_date(test_db):
    assert importer.insert_into_db(test_db, {'USD': 1.08}, date(2024, 3, 15)) == 1
    row = test_db.query(ExchangeRate).one()
    assert row.published_on == date(2024, 3, 15)


def test_reimporting_the_same_publication_is_a_no_op(test_db):
    importer.insert_into_db(test_db, {'USD': 1.08, 'JPY': 162.0}, date(2024, 3, 15))
    assert importer.insert_into_db(test_db, {'USD': 1.08, 'JPY': 162.0}, date(2024, 3, 15)) == 0
    assert test_db.query(ExchangeRate).count() == 2


def test_new_publication_day_adds_rows_with_change(test_db):
    importer.insert_into_db(test_db, {'USD': 1.08}, date(2024, 3, 14))
    importer.insert_into_db(test_db, {'USD': 1.09}, date(2024, 3, 15))
    latest = test_db.query(ExchangeRate).filter_by(published_on=date(2024, 3, 15)).one()
    assert latest.change == pytest.approx(0.01)


def test_latest_endpoint_returns_only_the_newest_publication(test_client, test_db):
    importer.insert_into_db(test_db, {'USD': 1.08, 'GBP': 0.85}, date(2024, 3, 14))
    importer.insert_into_db(test_db, {'USD': 1.09, 'GBP': 0.86}, date(2024, 3, 15))
    body = test_client.get('/exchange-rates/latest').json()
    assert body['published_on'] == '2024-03-15'
    assert [row['currency'] for row in body['rates']] == ['GBP', 'USD']
    assert all(row['published_on'] == '2024-03-15' for row in body['rates'])


def test_latest_endpoint_is_empty_before_any_import(test_client):
    assert test_client.get('/exchange-rates/latest').json() == {'published_on': None, 'rates': []}


def test_ensure_schema_adds_the_column_to_a_pre_existing_database():
    legacy = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    with legacy.begin() as connection:
        connection.execute(text(
            'CREATE TABLE exchange_rate (id INTEGER PRIMARY KEY, created_at DATETIME, updated_at DATETIME, '
            'currency VARCHAR NOT NULL, rate FLOAT NOT NULL, change FLOAT)'
        ))
        connection.execute(text("INSERT INTO exchange_rate (currency, rate) VALUES ('USD', 1.1)"))

    ensure_schema(legacy)
    ensure_schema(legacy)

    columns = {column['name'] for column in inspect(legacy).get_columns('exchange_rate')}
    indexes = {index['name'] for index in inspect(legacy).get_indexes('exchange_rate')}
    assert 'published_on' in columns
    assert 'ux_exchange_rate_currency_published_on' in indexes
    with legacy.connect() as connection:
        assert connection.execute(text('SELECT published_on FROM exchange_rate')).scalar() is None
