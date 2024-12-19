import os
from typing import Generator

from sqlalchemy import Column, DateTime, Integer, create_engine, func, inspect, text
from sqlalchemy.orm import Session, declarative_base, declared_attr, sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./exchange_rate.db')

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False} if SQLALCHEMY_DATABASE_URL.startswith('sqlite') else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class BaseModel:
    '''
    This class will not create table itself
    All other models would inherit from this class
    '''

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


Base = declarative_base(cls=BaseModel)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema(bind=engine) -> None:
    '''Create missing tables and add columns introduced after a database was first created.

    There is no migration tool in this prototype; the only change so far is the
    nullable ``exchange_rate.published_on`` column and its unique index.
    '''
    Base.metadata.create_all(bind=bind)
    columns = {column['name'] for column in inspect(bind).get_columns('exchange_rate')}
    if 'published_on' in columns:
        return
    with bind.begin() as connection:
        connection.execute(text('ALTER TABLE exchange_rate ADD COLUMN published_on DATE'))
        connection.execute(text(
            'CREATE INDEX IF NOT EXISTS ix_exchange_rate_published_on ON exchange_rate (published_on)'
        ))
        connection.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS ux_exchange_rate_currency_published_on '
            'ON exchange_rate (currency, published_on)'
        ))
