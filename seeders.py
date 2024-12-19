import argparse
from pathlib import Path

from database import SessionLocal, ensure_schema
from utils.exchange_rate import fetch_and_store_exchange_rates, insert_into_db, parse_feed


def seed_data(feed_files=()):
    ensure_schema()
    if not feed_files:
        published_on, inserted = fetch_and_store_exchange_rates()
        print(f'ECB publication {published_on}: {inserted} new rows')
        return
    for feed_file in feed_files:
        snapshot = parse_feed(Path(feed_file).read_bytes())
        with SessionLocal() as session:
            inserted = insert_into_db(session, snapshot.rates, snapshot.published_on)
        print(f'{feed_file} ({snapshot.published_on}): {inserted} new rows')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import ECB reference rates into the local database.')
    parser.add_argument(
        'feed_files', nargs='*', metavar='FEED.xml',
        help='saved daily feed files to import in order, instead of downloading the live feed',
    )
    seed_data(parser.parse_args().feed_files)
