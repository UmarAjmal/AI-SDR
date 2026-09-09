import logging
import random
import time
import functools
from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure

logger = logging.getLogger("codenter.worker")

def retry_with_jitter(
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter_range: tuple[float, float] = (0.8, 1.2)
):
    """
    Decorator implementing exponential backoff with randomized jitter
    for Celery tasks to prevent thundering herd and provider rate limit bursts.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self: Task, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                retries = self.request.retries
                if retries >= max_retries:
                    logger.error(
                        f"Task {self.name} [{self.request.id}] failed permanently after {retries} retries: {exc}"
                    )
                    raise exc

                # Exponential delay: base * (2 ** retries)
                calc_delay = min(base_delay * (2 ** retries), max_delay)
                # Apply randomized jitter
                jitter = random.uniform(jitter_range[0], jitter_range[1])
                actual_delay = calc_delay * jitter

                logger.warning(
                    f"Task {self.name} [{self.request.id}] failed ({exc}). "
                    f"Retrying in {actual_delay:.2f}s (Attempt {retries + 1}/{max_retries})..."
                )
                raise self.retry(exc=exc, countdown=actual_delay)
        return wrapper
    return decorator

@task_prerun.connect
def on_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **other):
    """
    Injects correlation context, workspace_id, and task metadata before execution.
    """
    kwargs_dict = kwargs or {}
    workspace_id = kwargs_dict.get("workspace_id", "GLOBAL_SYSTEM")
    trace_id = kwargs_dict.get("trace_id", task_id)
    
    # Store in task context
    if task:
        task._execution_start_time = time.time()
        task._workspace_id = workspace_id
        task._trace_id = trace_id

    logger.info(
        f"[START] Task={sender.name if sender else 'Unknown'} "
        f"TaskID={task_id} WorkspaceID={workspace_id} TraceID={trace_id}"
    )

@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **other):
    duration = 0.0
    workspace_id = "UNKNOWN"
    if task:
        start_time = getattr(task, "_execution_start_time", None)
        if start_time:
            duration = time.time() - start_time
        workspace_id = getattr(task, "_workspace_id", "UNKNOWN")

    logger.info(
        f"[FINISH] Task={sender.name if sender else 'Unknown'} "
        f"TaskID={task_id} WorkspaceID={workspace_id} State={state} Duration={duration:.3f}s"
    )

@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, traceback=None, **other):
    logger.error(
        f"[ERROR] Task={sender.name if sender else 'Unknown'} TaskID={task_id} Exception={exception}"
    )
