from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .models import TestExecution
from .realtime import execution_group_name, project_group_name


class ExecutionStreamConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close(code=4401)
            return

        self.execution_id = self.scope['url_route']['kwargs'].get('execution_id')
        self.project_id = self.scope['url_route']['kwargs'].get('project_id')
        self.group_names = []

        if self.execution_id is not None:
            allowed, project_id = await self._can_access_execution(self.execution_id)
            if not allowed:
                await self.close(code=4403)
                return
            self.group_names = [
                execution_group_name(self.execution_id),
                project_group_name(project_id),
            ]
        elif self.project_id is not None:
            allowed = await self._can_access_project(self.project_id)
            if not allowed:
                await self.close(code=4403)
                return
            self.group_names = [project_group_name(self.project_id)]
        else:
            await self.close(code=4400)
            return

        for group_name in self.group_names:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()
        await self.send_json(
            {
                'event': 'connection.ready',
                'execution_id': self.execution_id,
                'project_id': self.project_id,
            }
        )

    async def disconnect(self, close_code):
        for group_name in getattr(self, 'group_names', []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def execution_event(self, event):
        await self.send_json(event['payload'])

    @database_sync_to_async
    def _can_access_execution(self, execution_id: int):
        user = self.scope['user']
        queryset = self._visible_executions(user)
        execution = queryset.filter(id=execution_id).select_related('project').first()
        if execution is None:
            return False, None
        return True, execution.project_id

    @database_sync_to_async
    def _can_access_project(self, project_id: int):
        user = self.scope['user']
        return self._visible_executions(user).filter(project_id=project_id).exists()

    def _visible_executions(self, user):
        role = getattr(getattr(user, 'profile', None), 'role', None)
        if user.is_superuser or role == 'admin':
            return TestExecution.objects.all()
        return TestExecution.objects.filter(triggered_by=user)
