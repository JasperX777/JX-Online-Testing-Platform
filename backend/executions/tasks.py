import threading

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import ExecutionSchedule, TestExecution
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


@shared_task
def dispatch_due_execution_schedules():
    dispatched_ids = []
    due_schedule_ids = list(
        ExecutionSchedule.objects.filter(
            status=ExecutionSchedule.Status.PENDING,
            scheduled_for__lte=timezone.now(),
        ).values_list('id', flat=True)
    )

    for schedule_id in due_schedule_ids:
        with transaction.atomic():
            schedule = ExecutionSchedule.objects.select_for_update().get(id=schedule_id)
            if schedule.status != ExecutionSchedule.Status.PENDING:
                continue

            execution = TestExecution.objects.create(
                project=schedule.project,
                testcase=schedule.testcase,
                triggered_by=schedule.created_by,
                status=TestExecution.Status.PENDING,
            )
            initialize_execution(execution=execution)
            schedule.execution = execution
            schedule.status = ExecutionSchedule.Status.DISPATCHED
            schedule.dispatched_at = timezone.now()
            schedule.save(update_fields=['execution', 'status', 'dispatched_at'])

        dispatch_test_execution(execution.id)
        dispatched_ids.append(execution.id)

    return dispatched_ids
