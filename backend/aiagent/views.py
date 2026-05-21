from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AIAgentMessage, AIAgentSession
from .serializers import AIAgentSessionSerializer
from .services import run_mock_agent, serialize_agent_result


class AIAgentSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = (
            AIAgentSession.objects.filter(user=request.user)
            .select_related('project')
            .prefetch_related('messages')[:10]
        )
        return Response(AIAgentSessionSerializer(sessions, many=True).data)


class AIAgentSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        session = AIAgentSession.objects.filter(id=session_id, user=request.user).first()
        if not session:
            return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIAgentChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = (request.data.get('message') or '').strip()
        session_id = request.data.get('session_id')

        if not message:
            return Response({'detail': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        session = self._get_or_create_session(request.user, session_id, message)
        AIAgentMessage.objects.create(session=session, role=AIAgentMessage.Role.USER, content=message)

        result = run_mock_agent(session=session, user=request.user, message=message)
        payload = serialize_agent_result(result)
        assistant_message = AIAgentMessage.objects.create(
            session=session,
            role=AIAgentMessage.Role.ASSISTANT,
            content=result.reply,
            metadata={
                'needs_project_confirmation': result.needs_project_confirmation,
                'matched_project': payload['matched_project'],
                'project_candidates': payload['project_candidates'],
                'generated_testcase_ids': [item['id'] for item in payload['generated_testcases']],
                'execution_ids': [item['id'] for item in payload['executions']],
                'auto_run': result.auto_run,
            },
        )

        session.refresh_from_db()
        payload['session'] = AIAgentSessionSerializer(session).data
        payload['assistant_message_id'] = assistant_message.id
        return Response(payload, status=status.HTTP_200_OK)

    def _get_or_create_session(self, user, session_id, message):
        if session_id:
            session = AIAgentSession.objects.filter(id=session_id, user=user).first()
            if session:
                return session

        title = message[:80]
        return AIAgentSession.objects.create(user=user, title=title)
