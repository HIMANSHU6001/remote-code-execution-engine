"""Celery Beat periodic task schedule."""
from celery.schedules import crontab

beat_schedule = {
    # Mark stuck 'running' submissions as IE every 60 seconds
    "sweep-zombies": {
        "task": "worker.tasks.sweep_zombies",
        "schedule": 60.0,  # seconds
    },
    # Remove stale sandbox directories every 10 minutes
    "sweep-sandbox-dirs": {
        "task": "worker.tasks.sweep_sandbox_dirs",
        "schedule": 600.0,  # seconds
    },
}
