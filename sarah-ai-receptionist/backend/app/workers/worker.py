from arq.connections import RedisSettings
from arq.cron import cron
from app.config.settings import get_settings
from app.workers.tasks import summarize_call, send_reminders

settings = get_settings()


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions = [summarize_call, send_reminders]
    cron_jobs = [cron(send_reminders, hour=set(range(24)), minute=0)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
