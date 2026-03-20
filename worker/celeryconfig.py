"""Celery configuration for the RCE worker."""
from config.settings import settings

# Broker / backend
broker_url = settings.REDIS_URL           # DB 0 — task queue
result_backend = settings.REDIS_RESULT_URL  # DB 1 — result backend

# Serialisation
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Reliability
task_acks_late = True              # ack only after task completes (no message loss on crash)
worker_prefetch_multiplier = 1      # one task at a time per worker process
task_track_started = True           # publish STARTED state when task begins

# Routing — single default queue
task_default_queue = "default"

# Celery Beat periodic task schedule (imported from beat_schedule module)
from worker.beat_schedule import beat_schedule  # noqa: E402
