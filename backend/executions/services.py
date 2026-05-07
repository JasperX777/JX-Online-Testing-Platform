from django.utils import timezone

from .automation import AutomationDependencyError, execute_steps
from .models import ExecutionLog, ExecutionStepResult, TestExecution
from .realtime import broadcast_execution_event
from .reports import store_execution_report


def _serialize_execution_update(execution: TestExecution):
    return TestExecution.objects.select_related('project', 'testcase', 'triggered_by', 'report').prefetch_related('step_results').get(id=execution.id)


def _write_execution_log(*, execution: TestExecution, level: str, message: str):
    refreshed_execution = _serialize_execution_update(execution)
    log = ExecutionLog.objects.create(
        execution=execution,
        project=execution.project,
        testcase=execution.testcase,
        level=level,
        message=message,
    )
    broadcast_execution_event(event='execution.log', execution=refreshed_execution, log=log)
    return log


def initialize_execution(*, execution: TestExecution):
    if execution.step_results.exists():
        return execution

    step_results = [
        ExecutionStepResult(
            execution=execution,
            step_no=step['step_no'],
            step_title=step.get('step_title', ''),
            description=step.get('description', ''),
            action=step['action'],
            target=step['target'],
            locator_type=step.get('locator_type', 'css'),
            selector=step.get('selector', ''),
            value=step.get('value', ''),
            note=step.get('note', ''),
        )
        for step in (execution.testcase.steps_json if execution.testcase else [])
    ]
    if step_results:
        ExecutionStepResult.objects.bulk_create(step_results)

    execution.status = TestExecution.Status.PENDING
    execution.current_step_no = 1 if step_results else None
    execution.started_at = None
    execution.finished_at = None
    execution.result_summary = ''
    execution.failure_reason = ''
    execution.failed_step_no = None
    execution.save(
        update_fields=[
            'status',
            'current_step_no',
            'started_at',
            'finished_at',
            'result_summary',
            'failure_reason',
            'failed_step_no',
        ]
    )
    broadcast_execution_event(event='execution.pending', execution=_serialize_execution_update(execution))
    return execution


def _mark_step_passed(*, execution: TestExecution, step_result: ExecutionStepResult):
    step_result.status = ExecutionStepResult.Status.PASSED
    step_result.error_message = ''
    step_result.executed_at = timezone.now()
    step_result.save(update_fields=['status', 'error_message', 'executed_at'])
    _write_execution_log(
        execution=execution,
        level=ExecutionLog.Level.INFO,
        message=f'Step {step_result.step_no} passed.',
    )
    broadcast_execution_event(event='execution.step.updated', execution=_serialize_execution_update(execution))


def _mark_step_failed(*, execution: TestExecution, step_result: ExecutionStepResult, reason: str, screenshot_path: str = ''):
    step_result.status = ExecutionStepResult.Status.FAILED
    step_result.error_message = reason
    step_result.screenshot_path = screenshot_path
    step_result.executed_at = timezone.now()
    step_result.save(update_fields=['status', 'error_message', 'screenshot_path', 'executed_at'])

    execution.status = TestExecution.Status.FAILED
    execution.failed_step_no = step_result.step_no
    execution.failure_reason = reason
    execution.result_summary = reason
    execution.current_step_no = step_result.step_no
    execution.finished_at = timezone.now()
    execution.save(
        update_fields=[
            'status',
            'failed_step_no',
            'failure_reason',
            'result_summary',
            'current_step_no',
            'finished_at',
        ]
    )

    _write_execution_log(
        execution=execution,
        level=ExecutionLog.Level.ERROR,
        message=f'Step {step_result.step_no} failed: {reason}',
    )
    report = store_execution_report(execution=_serialize_execution_update(execution))
    broadcast_execution_event(
        event='execution.finished',
        execution=_serialize_execution_update(execution),
        report=report,
    )


def _mark_execution_success(*, execution: TestExecution):
    execution.status = TestExecution.Status.SUCCESS
    execution.current_step_no = None
    execution.result_summary = 'Execution completed successfully.'
    execution.failure_reason = ''
    execution.failed_step_no = None
    execution.finished_at = timezone.now()
    execution.save(
        update_fields=[
            'status',
            'current_step_no',
            'result_summary',
            'failure_reason',
            'failed_step_no',
            'finished_at',
        ]
    )
    _write_execution_log(
        execution=execution,
        level=ExecutionLog.Level.INFO,
        message=f'Execution {execution.id} completed successfully.',
    )
    report = store_execution_report(execution=_serialize_execution_update(execution))
    broadcast_execution_event(
        event='execution.finished',
        execution=_serialize_execution_update(execution),
        report=report,
    )


def run_test_execution(*, execution: TestExecution):
    execution = _serialize_execution_update(execution)
    if execution.status not in {TestExecution.Status.PENDING, TestExecution.Status.RUNNING}:
        return execution

    if execution.started_at is None:
        execution.started_at = timezone.now()
        execution.status = TestExecution.Status.RUNNING
        execution.save(update_fields=['started_at', 'status'])

    step_results = list(execution.step_results.order_by('step_no'))
    if not step_results:
        execution.status = TestExecution.Status.FAILED
        execution.result_summary = 'Execution has no steps to run.'
        execution.failure_reason = execution.result_summary
        execution.finished_at = timezone.now()
        execution.save(update_fields=['status', 'result_summary', 'failure_reason', 'finished_at'])
        report = store_execution_report(execution=_serialize_execution_update(execution))
        broadcast_execution_event(event='execution.finished', execution=_serialize_execution_update(execution), report=report)
        return execution

    _write_execution_log(
        execution=execution,
        level=ExecutionLog.Level.INFO,
        message=f'Execution {execution.id} started automated browser run.',
    )
    broadcast_execution_event(event='execution.started', execution=_serialize_execution_update(execution))

    try:
        outcomes = execute_steps(execution=execution, step_results=step_results)
    except AutomationDependencyError as exc:
        _mark_step_failed(
            execution=execution,
            step_result=step_results[0],
            reason=str(exc),
            screenshot_path='',
        )
        return _serialize_execution_update(execution)

    step_results_by_no = {step_result.step_no: step_result for step_result in step_results}
    for outcome in outcomes:
        step_result = step_results_by_no.get(outcome['step_no'])
        if step_result is None:
            continue
        execution.current_step_no = step_result.step_no
        execution.save(update_fields=['current_step_no'])
        _write_execution_log(
            execution=execution,
            level=ExecutionLog.Level.INFO,
            message=f'Started step {step_result.step_no}: {step_result.action} ({step_result.target or step_result.step_title}).',
        )
        broadcast_execution_event(event='execution.step.started', execution=_serialize_execution_update(execution))
        if outcome['status'] == 'passed':
            _mark_step_passed(execution=execution, step_result=step_result)
            continue

        _mark_step_failed(
            execution=execution,
            step_result=step_result,
            reason=outcome['error_message'],
            screenshot_path=outcome['screenshot_path'],
        )
        return _serialize_execution_update(execution)

    _mark_execution_success(execution=execution)
    return _serialize_execution_update(execution)
