import subprocess
import sys

from django.conf import settings
from django.utils import timezone

from .models import ExecutionLog, TestExecution


def run_test_execution(*, execution: TestExecution):
    execution.status = TestExecution.Status.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=['status', 'started_at'])

    ExecutionLog.objects.create(
        project=execution.project,
        testcase=execution.testcase,
        level=ExecutionLog.Level.INFO,
        message=f'Execution {execution.id} started.',
    )

    cmd = [sys.executable, '-m', 'pytest', '-q']
    if execution.testcase and execution.testcase.pytest_target:
        cmd.append(execution.testcase.pytest_target)

    completed = subprocess.run(
        cmd,
        cwd=settings.BASE_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )

    summary_parts = [part for part in [completed.stdout.strip(), completed.stderr.strip()] if part]
    summary = '\n'.join(summary_parts)

    execution.exit_code = completed.returncode
    execution.result_summary = summary
    execution.finished_at = timezone.now()
    execution.status = (
        TestExecution.Status.SUCCESS
        if completed.returncode == 0
        else TestExecution.Status.FAILED
    )
    execution.save(update_fields=['exit_code', 'result_summary', 'finished_at', 'status'])

    ExecutionLog.objects.create(
        project=execution.project,
        testcase=execution.testcase,
        level=(ExecutionLog.Level.INFO if completed.returncode == 0 else ExecutionLog.Level.ERROR),
        message=f'Execution {execution.id} finished with exit code {completed.returncode}.',
    )

    return execution
