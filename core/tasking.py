import importlib
import threading
import traceback

from django.conf import settings
from django.utils import timezone

from .models import BackgroundTaskLog


TASK_REGISTRY = {}


def registered_task(name):
    """Register a callable task by stable name."""
    def decorator(func):
        TASK_REGISTRY[name] = func
        return func

    return decorator


def dispatch_task(name, *args, **kwargs):
    """Dispatch a registered task through the configured backend."""
    _load_default_tasks()
    if name not in TASK_REGISTRY:
        raise ValueError(f"Unknown background task: {name}")

    backend = get_task_backend()
    if getattr(settings, "BACKGROUND_TASK_SYNCHRONOUS", False):
        backend = BackgroundTaskLog.BACKEND_INLINE
    task_log = BackgroundTaskLog.objects.create(
        task_name=name,
        backend=backend,
        args=list(args),
        kwargs=kwargs,
    )
    if backend == BackgroundTaskLog.BACKEND_INLINE:
        run_task_log(task_log.id)
    elif backend == BackgroundTaskLog.BACKEND_THREADING:
        thread = threading.Thread(target=run_task_log, args=(task_log.id,), daemon=True)
        thread.start()
    elif backend == BackgroundTaskLog.BACKEND_CELERY:
        from .tasks import run_registered_task

        run_registered_task.delay(task_log.id)
    else:
        raise ValueError(f"Unsupported background task backend: {backend}")
    return task_log


def get_task_backend():
    """Return the normalized backend configured for this environment."""
    backend = getattr(settings, "BACKGROUND_TASK_BACKEND", BackgroundTaskLog.BACKEND_THREADING)
    if backend not in {BackgroundTaskLog.BACKEND_THREADING, BackgroundTaskLog.BACKEND_CELERY}:
        raise ValueError(f"Unsupported BACKGROUND_TASK_BACKEND: {backend}")
    return backend


def run_task_log(task_log_id):
    """Execute a pending task log and persist status, result, or error."""
    _load_default_tasks()
    task_log = BackgroundTaskLog.objects.get(id=task_log_id)
    task_log.status = BackgroundTaskLog.STATUS_RUNNING
    task_log.started_at = timezone.now()
    task_log.save(update_fields=["status", "started_at"])
    try:
        task = TASK_REGISTRY[task_log.task_name]
        result = task(*task_log.args, **task_log.kwargs)
    except Exception as exc:
        task_log.status = BackgroundTaskLog.STATUS_FAILED
        task_log.error_message = f"{exc}\n{traceback.format_exc()}"
        task_log.finished_at = timezone.now()
        task_log.save(update_fields=["status", "error_message", "finished_at"])
        raise
    task_log.status = BackgroundTaskLog.STATUS_SUCCESS
    task_log.result = _json_safe_result(result)
    task_log.finished_at = timezone.now()
    task_log.save(update_fields=["status", "result", "finished_at"])
    return result


def _load_default_tasks():
    """Import the default task registry once."""
    if not TASK_REGISTRY:
        importlib.import_module("core.jobs")


def _json_safe_result(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return {"value": str(value)}
