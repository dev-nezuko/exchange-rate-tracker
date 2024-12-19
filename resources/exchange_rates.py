from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from database import get_db
from models import ExchangeRate
from schemas.exchange_rates import ExchangeRateResponse

router = APIRouter()


@router.get(
    '/exchange-rates/',
    status_code=status.HTTP_200_OK,
    response_model=ExchangeRateResponse,
)
def get_exchange_rates(db: Session = Depends(get_db)):
    '''
    Will return all stored rates
    '''

    today = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())

    exchange_rates = (
        db.query(ExchangeRate).filter(ExchangeRate.created_at >= today, ExchangeRate.created_at < today + timedelta(days=1)).order_by(ExchangeRate.currency, ExchangeRate.id).all()
    )

    return ExchangeRateResponse(rates=exchange_rates)
