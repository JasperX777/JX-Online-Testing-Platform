from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import ExecutionLogSerializer, ExecutionReportSerializer, TestExecutionSerializer


def execution_group_name(execution_id: int) -> str:
    return f'execution_{execution_id}'


def project_group_name(project_id: int) -> str:
    return f'project_{project_id}_executions'


def _serialize_payload(*, event: str, execution, log=None, report=None) -> dict:
    payload = {
        'event': event,
        'execution': TestExecutionSerializer(execution).data,
    }
    if log is not None:
        payload['log'] = ExecutionLogSerializer(log).data
    if report is not None:
        payload['report'] = ExecutionReportSerializer(report).data
    return payload


def broadcast_execution_event(*, event: str, execution, log=None, report=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = _serialize_payload(event=event, execution=execution, log=log, report=report)
    message = {
        'type': 'execution.event',
        'payload': payload,
    }
    async_to_sync(channel_layer.group_send)(execution_group_name(execution.id), message)
    async_to_sync(channel_layer.group_send)(project_group_name(execution.project_id), message)
