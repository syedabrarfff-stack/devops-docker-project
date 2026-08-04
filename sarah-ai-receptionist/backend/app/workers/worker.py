from arq.connections import RedisSettings
from arq.cron import cron

from app.config.settings import get_settings
from app.workers.tasks import enforce_call_retention, send_reminders, summarize_call

settings = get_settings()


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions = [summarize_call, send_reminders, enforce_call_retention]
    cron_jobs = [
        cron(send_reminders, hour=set(range(24)), minute=0),
        cron(enforce_call_retention, hour=3, minute=0),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
