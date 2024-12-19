from contextlib import contextmanager
from pathlib import Path

import seeders
from models import ExchangeRate

SAMPLES = sorted((Path(__file__).resolve().parent.parent / 'samples').glob('eurofxref-*.xml'))


def test_seeding_from_saved_feeds_never_touches_the_network(test_db, monkeypatch):
    @contextmanager
    def session_factory():
        yield test_db

    def no_network():
        raise AssertionError('live feed must not be fetched')

    monkeypatch.setattr(seeders, 'SessionLocal', session_factory)
    monkeypatch.setattr(seeders, 'ensure_schema', lambda: None)
    monkeypatch.setattr(seeders, 'fetch_and_store_exchange_rates', no_network)

    seeders.seed_data([str(path) for path in SAMPLES])
    seeders.seed_data([str(SAMPLES[-1])])

    assert len(SAMPLES) == 2
    assert test_db.query(ExchangeRate).count() == 60
    latest = test_db.query(ExchangeRate).filter_by(currency='BGN').order_by(ExchangeRate.id.desc()).first()
    assert latest.change == 0
