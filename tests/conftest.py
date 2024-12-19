import random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import ExchangeRate

SQLALCHEMY_DATABASE_URL = 'sqlite://'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)


client = TestClient(app)


@pytest.fixture
def test_exchange_rate():
    exchange_rate = ExchangeRate(
        currency='USD',
        rate=random.randint(2, 5),
        change=random.random(),
    )

    yield exchange_rate


@pytest.fixture
def test_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

    with engine.connect() as connection:
        connection.execute(text('DELETE FROM exchange_rate;'))
        connection.commit()


@pytest.fixture
def test_client():
    yield client
