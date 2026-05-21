from django.urls import path

from .views import AIAgentChatView, AIAgentSessionDetailView, AIAgentSessionListView


urlpatterns = [
    path('ai-agent/sessions/', AIAgentSessionListView.as_view(), name='ai-agent-sessions'),
    path('ai-agent/sessions/<int:session_id>/', AIAgentSessionDetailView.as_view(), name='ai-agent-session-detail'),
    path('ai-agent/chat/', AIAgentChatView.as_view(), name='ai-agent-chat'),
]
