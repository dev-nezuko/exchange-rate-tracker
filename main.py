import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401  (registers the ORM tables on Base.metadata)
from database import ensure_schema
from resources import exchange_rates
from utils.exchange_rate import fetch_and_store_exchange_rates

# The ECB publishes around 16:00 CET on TARGET working days. 15:30 UTC is after
# that in both winter (15:00 UTC) and summer (14:00 UTC), so no tz database is needed.
ECB_PUBLICATION_TRIGGER = CronTrigger(day_of_week='mon-fri', hour=15, minute=30, timezone='UTC')
STATIC_DIR = Path(__file__).resolve().parent / 'static'


def create_app(enable_scheduler=None):
    if enable_scheduler is None:
        enable_scheduler = os.getenv('ENABLE_SCHEDULER', 'false').lower() == 'true'

    @asynccontextmanager
    async def lifespan(_app):
        ensure_schema()
        scheduler = None
        if enable_scheduler:
            scheduler = BackgroundScheduler(timezone='UTC')
            scheduler.add_job(
                fetch_and_store_exchange_rates,
                ECB_PUBLICATION_TRIGGER,
                id='daily_task',
                max_instances=1,
                coalesce=True,
            )
            scheduler.start()
        try:
            yield
        finally:
            if scheduler:
                scheduler.shutdown()

    application = FastAPI(lifespan=lifespan)

    @application.get('/')
    def health_check():
        return {'message': 'System is up and running'}

    @application.get('/rates', include_in_schema=False)
    def rates_board():
        return FileResponse(STATIC_DIR / 'rates.html')

    application.include_router(exchange_rates.router)
    application.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
    return application


app = create_app()
