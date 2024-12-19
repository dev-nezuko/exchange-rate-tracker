from database import ensure_schema
from utils.exchange_rate import fetch_and_store_exchange_rates


def seed_data():
    ensure_schema()
    published_on, inserted = fetch_and_store_exchange_rates()
    print(f'ECB publication {published_on}: {inserted} new rows')


if __name__ == '__main__':
    seed_data()
