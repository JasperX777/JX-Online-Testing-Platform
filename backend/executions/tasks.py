from celery import shared_task

from .models import TestExecution
from .services import run_test_execution


@shared_task
def run_test_execution_task(execution_id: int):
    execution = TestExecution.objects.get(id=execution_id)
    run_test_execution(execution=execution)
