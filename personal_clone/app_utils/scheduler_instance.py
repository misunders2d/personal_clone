import os

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Use the same database as the ADK SessionService, but synchronous for APScheduler
db_url = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/personal_clone.db",
)
# APScheduler needs a synchronous driver
sync_db_url = db_url.replace("+aiosqlite", "")

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=sync_db_url)},
)
