from contextlib import contextmanager
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from main import ECB_PUBLICATION_TRIGGER, create_app
from models import ExchangeRate
from utils import exchange_rate as importer


class Response:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    def iter_content(self, _size):
        yield self.content


def test_xml_import_parses_positive_rates_without_live_network(monkeypatch):
    payload = (
        b'<Envelope><Cube><Cube time="2024-01-01">'
        b'<Cube currency="USD" rate="1.2"/><Cube currency="GBP" rate="0.8"/>'
        b'</Cube></Cube></Envelope>'
    )
    fetch = Mock(return_value=Response(payload))
    monkeypatch.setattr(importer.requests, 'get', fetch)
    assert importer.fetch_exchange_rates() == (date(2024, 1, 1), {'USD': 1.2, 'GBP': 0.8})
    assert fetch.call_args.kwargs == {'timeout': 15, 'stream': True}


@pytest.mark.parametrize('payload', [
    b'<root/>',
    b'<!DOCTYPE root><root/>',
    b'<Envelope><Cube><Cube time="2024-01-01"><Cube currency="USD" rate="NaN"/></Cube></Cube></Envelope>',
    b'<Envelope><Cube><Cube time="2024-01-01"><Cube currency="USD" rate="-1"/></Cube></Cube></Envelope>',
    b'<Envelope><Cube><Cube time="2024-01-01"><Cube currency="usd" rate="1.1"/></Cube></Cube></Envelope>',
    b'<Envelope><Cube><Cube time="2024-01-01"><Cube currency="USD" rate="1.1"/>'
    b'<Cube currency="USD" rate="1.2"/></Cube></Cube></Envelope>',
])
def test_invalid_xml_rates_are_rejected(monkeypatch, payload):
    monkeypatch.setattr(importer.requests, 'get', lambda *args, **kwargs: Response(payload))
    with pytest.raises(ValueError):
        importer.fetch_exchange_rates()


def test_oversized_response_is_rejected(monkeypatch):
    payload = b' ' * (importer.MAX_FEED_BYTES + 1)
    monkeypatch.setattr(importer.requests, 'get', lambda *args, **kwargs: Response(payload))
    with pytest.raises(ValueError, match='exceeds limit'):
        importer.fetch_exchange_rates()


@pytest.mark.parametrize('payload', [
    b'<Envelope><Cube',
    b'<Envelope><Cube time="2024-01-01"><Cube currency="USD"/></Cube></Envelope>',
    b'<Envelope><Cube time="2024-01-01"><Cube currency="USD" rate="abc"/></Cube></Envelope>',
])
def test_malformed_feed_surfaces_as_value_error(monkeypatch, payload):
    monkeypatch.setattr(importer.requests, 'get', lambda *args, **kwargs: Response(payload))
    with pytest.raises(ValueError):
        importer.fetch_exchange_rates()


def test_delta_uses_the_previous_stored_sample(test_db):
    importer.insert_into_db(test_db, {'USD': 1.0, 'GBP': 0.8})
    importer.insert_into_db(test_db, {'USD': 1.2, 'GBP': 0.7})
    latest = test_db.query(ExchangeRate).filter_by(currency='USD').order_by(ExchangeRate.id.desc()).first()
    assert latest.change == pytest.approx(0.2)
    assert test_db.query(ExchangeRate).count() == 4


def test_failed_batch_rolls_back_all_new_rows(test_db):
    importer.insert_into_db(test_db, {'USD': 1.0})

    def fail(*args):
        raise RuntimeError('synthetic storage failure')

    event.listen(test_db, 'before_flush', fail)
    try:
        with pytest.raises(RuntimeError):
            importer.insert_into_db(test_db, {'USD': 1.2, 'GBP': 0.8})
    finally:
        event.remove(test_db, 'before_flush', fail)
    assert test_db.query(ExchangeRate).count() == 1
    assert test_db.query(ExchangeRate).first().rate == 1.0


def test_scheduled_import_owns_and_closes_its_session(test_db, monkeypatch):
    closed = []

    @contextmanager
    def session_factory():
        try:
            yield test_db
        finally:
            test_db.close()
            closed.append(True)

    monkeypatch.setattr(importer, 'SessionLocal', session_factory)
    monkeypatch.setattr(
        importer, 'fetch_exchange_rates',
        lambda: importer.FeedSnapshot(date(2024, 1, 2), {'USD': 1.2}),
    )
    assert importer.fetch_and_store_exchange_rates() == (date(2024, 1, 2), 1)
    assert closed == [True]
    assert test_db.query(ExchangeRate).count() == 1


def test_schema_initialization_is_lifespan_only_and_scheduler_can_stay_off():
    with patch('main.ensure_schema') as create, patch('main.BackgroundScheduler') as scheduler:
        app = create_app(enable_scheduler=False)
        create.assert_not_called()
        with TestClient(app) as client:
            assert client.get('/').status_code == 200
        create.assert_called_once()
        scheduler.assert_not_called()


def test_scheduled_import_runs_after_the_ecb_publishes_on_weekdays():
    friday_evening = datetime(2024, 1, 5, 16, 0, tzinfo=timezone.utc)
    next_run = ECB_PUBLICATION_TRIGGER.get_next_fire_time(None, friday_evening)
    assert (next_run.weekday(), next_run.hour, next_run.minute) == (0, 15, 30)
