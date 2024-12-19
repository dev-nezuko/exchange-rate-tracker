from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from database import get_db
from models import ExchangeRate
from schemas.exchange_rates import ExchangeRateResponse, LatestPublicationResponse

router = APIRouter()


@router.get(
    '/exchange-rates/',
    status_code=status.HTTP_200_OK,
    response_model=ExchangeRateResponse,
)
def get_exchange_rates(db: Session = Depends(get_db)):
    '''Rows imported during the current UTC day (an import log, not a snapshot).'''

    today = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())

    exchange_rates = (
        db.query(ExchangeRate)
        .filter(ExchangeRate.created_at >= today, ExchangeRate.created_at < today + timedelta(days=1))
        .order_by(ExchangeRate.currency, ExchangeRate.id)
        .all()
    )

    return ExchangeRateResponse(rates=exchange_rates)


@router.get(
    '/exchange-rates/latest',
    status_code=status.HTTP_200_OK,
    response_model=LatestPublicationResponse,
)
def get_latest_publication(db: Session = Depends(get_db)):
    '''All currencies from the most recent ECB publication day that has been imported.'''

    published_on = db.query(func.max(ExchangeRate.published_on)).scalar()
    if published_on is None:
        return LatestPublicationResponse(rates=[])

    exchange_rates = (
        db.query(ExchangeRate)
        .filter(ExchangeRate.published_on == published_on)
        .order_by(ExchangeRate.currency)
        .all()
    )
    return LatestPublicationResponse(published_on=published_on, rates=exchange_rates)
