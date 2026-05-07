import threading

from celery import shared_task

from .models import TestExecution
from .services import initialize_execution, run_test_execution


@shared_task
def run_test_execution_task(execution_id: int):
    execution = TestExecution.objects.get(id=execution_id)
    initialize_execution(execution=execution)
    run_test_execution(execution=execution)


def dispatch_test_execution(execution_id: int):
    try:
        run_test_execution_task.delay(execution_id)
    except Exception:
        thread = threading.Thread(
            target=run_test_execution_task.run,
            args=(execution_id,),
            daemon=True,
        )
        thread.start()
