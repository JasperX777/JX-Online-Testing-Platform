from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import ExecutionSchedule, TestExecution
from .services import create_execution, initialize_execution, mark_execution_dispatch_failed, run_test_execution


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=3)
def run_test_execution_task(self, execution_id: int):
    try:
        execution = TestExecution.objects.get(id=execution_id)
        initialize_execution(execution=execution)
        run_test_execution(execution=execution)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            execution = TestExecution.objects.filter(id=execution_id).first()
            if execution:
                mark_execution_dispatch_failed(
                    execution=execution,
                    reason=f'Execution task failed after {self.max_retries + 1} attempts: {exc}',
                )
        raise


def dispatch_test_execution(execution_id: int):
    return run_test_execution_task.delay(execution_id)


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

            execution = create_execution(
                project=schedule.project,
                testcase=schedule.testcase,
                triggered_by=schedule.created_by,
            )
            schedule.execution = execution
            schedule.status = ExecutionSchedule.Status.DISPATCHED
            schedule.dispatched_at = timezone.now()
            schedule.save(update_fields=['execution', 'status', 'dispatched_at'])

        try:
            dispatch_test_execution(execution.id)
            dispatched_ids.append(execution.id)
        except Exception as exc:
            reason = f'Unable to dispatch scheduled execution: {exc}'
            mark_execution_dispatch_failed(execution=execution, reason=reason)
            schedule.status = ExecutionSchedule.Status.FAILED
            schedule.failure_reason = reason
            schedule.save(update_fields=['status', 'failure_reason'])

    return dispatched_ids
