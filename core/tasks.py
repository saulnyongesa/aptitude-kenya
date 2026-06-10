from config.celery import app

from .tasking import run_task_log


@app.task(name="core.run_registered_task")
def run_registered_task(task_log_id):
    """Celery entrypoint for the shared task registry."""
    return run_task_log(task_log_id)
