from django.utils import timezone
from django.conf import settings

from .models import ExecutionReport, ExecutionStepResult, TestExecution


def _to_media_url(path: str) -> str:
    if not path:
        return ''
    media_root = str(settings.MEDIA_ROOT)
    if path.startswith(media_root):
        relative_path = path[len(media_root):].lstrip('/\\')
        return f"{settings.MEDIA_URL}{relative_path.replace('\\', '/')}"
    return path


def build_execution_report(*, execution: TestExecution) -> dict:
    step_results = execution.step_results.order_by('step_no')
    duration_seconds = None
    if execution.started_at and execution.finished_at:
        duration_seconds = (execution.finished_at - execution.started_at).total_seconds()

    passed_steps = step_results.filter(status=ExecutionStepResult.Status.PASSED).count()
    failed_steps = step_results.filter(status=ExecutionStepResult.Status.FAILED).count()
    pending_steps = step_results.filter(status=ExecutionStepResult.Status.PENDING).count()

    return {
        'execution': {
            'id': execution.id,
            'status': execution.status,
            'result_summary': execution.result_summary,
            'failure_reason': execution.failure_reason,
            'failed_step_no': execution.failed_step_no,
            'current_step_no': execution.current_step_no,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'finished_at': execution.finished_at.isoformat() if execution.finished_at else None,
            'duration_seconds': duration_seconds,
            'generated_at': timezone.now().isoformat(),
            'triggered_by': execution.triggered_by.username if execution.triggered_by else None,
        },
        'project': {
            'id': execution.project_id,
            'name': execution.project.name,
        },
        'testcase': {
            'id': execution.testcase_id,
            'title': execution.testcase.title if execution.testcase else None,
            'module': execution.testcase.module if execution.testcase else '',
            'scenario': execution.testcase.scenario if execution.testcase else '',
            'description': execution.testcase.description if execution.testcase else '',
        },
        'summary': {
            'total_steps': step_results.count(),
            'passed_steps': passed_steps,
            'failed_steps': failed_steps,
            'pending_steps': pending_steps,
            'failed_step_no': execution.failed_step_no,
            'failure_reason': execution.failure_reason,
        },
        'steps': [
            {
                'step_no': step.step_no,
                'step_title': step.step_title,
                'description': step.description,
                'action': step.action,
                'target': step.target,
                'locator_type': step.locator_type,
                'selector': step.selector,
                'value': step.value,
                'note': step.note,
                'status': step.status,
                'executor_note': step.executor_note,
                'error_message': step.error_message,
                'screenshot_path': step.screenshot_path,
                'screenshot_url': _to_media_url(step.screenshot_path),
                'executed_at': step.executed_at.isoformat() if step.executed_at else None,
            }
            for step in step_results
        ],
    }


def store_execution_report(*, execution: TestExecution) -> ExecutionReport:
    report, _ = ExecutionReport.objects.update_or_create(
        execution=execution,
        defaults={'report_data': build_execution_report(execution=execution)},
    )
    return report
