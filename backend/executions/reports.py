from django.utils import timezone

from .models import ExecutionReport, TestExecution


def build_execution_report(*, execution: TestExecution) -> dict:
    logs = execution.logs.order_by('created_at')
    duration_seconds = None
    if execution.started_at and execution.finished_at:
        duration_seconds = (execution.finished_at - execution.started_at).total_seconds()

    return {
        'execution': {
            'id': execution.id,
            'status': execution.status,
            'exit_code': execution.exit_code,
            'result_summary': execution.result_summary,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'finished_at': execution.finished_at.isoformat() if execution.finished_at else None,
            'duration_seconds': duration_seconds,
            'generated_at': timezone.now().isoformat(),
        },
        'project': {
            'id': execution.project_id,
            'name': execution.project.name,
        },
        'testcase': {
            'id': execution.testcase_id,
            'title': execution.testcase.title if execution.testcase else None,
            'test_type': execution.testcase.test_type if execution.testcase else None,
        },
        'logs': [
            {
                'id': log.id,
                'level': log.level,
                'message': log.message,
                'created_at': log.created_at.isoformat(),
            }
            for log in logs
        ],
        'totals': {
            'log_count': logs.count(),
        },
    }


def store_execution_report(*, execution: TestExecution) -> ExecutionReport:
    report, _ = ExecutionReport.objects.update_or_create(
        execution=execution,
        defaults={'report_data': build_execution_report(execution=execution)},
    )
    return report
