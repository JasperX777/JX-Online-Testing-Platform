from django.urls import path

from .consumers import ExecutionStreamConsumer

websocket_urlpatterns = [
    path('ws/executions/<int:execution_id>/', ExecutionStreamConsumer.as_asgi()),
    path('ws/projects/<int:project_id>/executions/', ExecutionStreamConsumer.as_asgi()),
]
