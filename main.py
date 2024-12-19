import os
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
import models
from database import Base, engine
from resources import exchange_rates
from utils.exchange_rate import fetch_and_store_exchange_rates


def create_app(enable_scheduler=None):
    if enable_scheduler is None:
        enable_scheduler = os.getenv('ENABLE_SCHEDULER', 'false').lower() == 'true'

    @asynccontextmanager
    async def lifespan(_app):
        Base.metadata.create_all(bind=engine)
        scheduler = None
        if enable_scheduler:
            scheduler = BackgroundScheduler(timezone='UTC')
            scheduler.add_job(fetch_and_store_exchange_rates, CronTrigger(hour=0, minute=2, timezone='UTC'), id='daily_task', max_instances=1, coalesce=True)
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

    application.include_router(exchange_rates.router)
    return application


app = create_app()
