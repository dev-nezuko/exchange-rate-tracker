from database import Base, engine
from utils.exchange_rate import fetch_and_store_exchange_rates

def seed_data():
    Base.metadata.create_all(bind=engine)
    print('====Seeding Data======')
    fetch_and_store_exchange_rates()
    print('====Data Seeded=======')


if __name__ == '__main__':
    seed_data()