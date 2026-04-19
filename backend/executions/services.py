from django.utils import timezone

from .models import ExecutionLog, TestExecution
from .realtime import broadcast_execution_event
from .reports import store_execution_report
from .runners import UnsupportedExecutionTypeError, get_execution_runner


def _write_execution_log(*, execution: TestExecution, level: str, message: str):
    log = ExecutionLog.objects.create(
        execution=execution,
        project=execution.project,
        testcase=execution.testcase,
        level=level,
        message=message,
    )
    broadcast_execution_event(event='execution.log', execution=execution, log=log)
    return log


def _finalize_execution(*, execution: TestExecution, exit_code: int, summary: str, succeeded: bool):
    execution.exit_code = exit_code
    execution.result_summary = summary
    execution.finished_at = timezone.now()
    execution.status = (
        TestExecution.Status.SUCCESS if succeeded else TestExecution.Status.FAILED
    )
    execution.save(update_fields=['exit_code', 'result_summary', 'finished_at', 'status'])

    _write_execution_log(
        execution=execution,
        level=(ExecutionLog.Level.INFO if succeeded else ExecutionLog.Level.ERROR),
        message=f'Execution {execution.id} finished with exit code {exit_code}.',
    )
    report = store_execution_report(execution=execution)
    broadcast_execution_event(event='execution.finished', execution=execution, report=report)
    return execution


def run_test_execution(*, execution: TestExecution):
    execution.status = TestExecution.Status.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=['status', 'started_at'])
    broadcast_execution_event(event='execution.started', execution=execution)

    test_type = getattr(execution.testcase, 'test_type', 'functional')
    _write_execution_log(
        execution=execution,
        level=ExecutionLog.Level.INFO,
        message=f'Execution {execution.id} started for {test_type} test.',
    )

    try:
        runner = get_execution_runner(execution.testcase)
        completed = runner.run(execution)
    except UnsupportedExecutionTypeError as exc:
        return _finalize_execution(
            execution=execution,
            exit_code=1,
            summary=str(exc),
            succeeded=False,
        )
    except Exception as exc:
        return _finalize_execution(
            execution=execution,
            exit_code=1,
            summary=f'Execution failed before completion: {exc}',
            succeeded=False,
        )

    summary_parts = [part for part in [completed.stdout.strip(), completed.stderr.strip()] if part]
    summary = '\n'.join(summary_parts)

    return _finalize_execution(
        execution=execution,
        exit_code=completed.returncode,
        summary=summary,
        succeeded=(completed.returncode == 0),
    )
