from rest_framework import serializers

from executions.serializers import TestExecutionSerializer
from testcases.serializers import TestCaseSerializer

from .models import AIAgentMessage, AIAgentSession


class AIAgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAgentMessage
        fields = ('id', 'role', 'content', 'metadata', 'created_at')
        read_only_fields = fields


class AIAgentSessionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    messages = AIAgentMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIAgentSession
        fields = ('id', 'project', 'project_name', 'title', 'context', 'created_at', 'updated_at', 'messages')
        read_only_fields = fields


class AIAgentChatResponseSerializer(serializers.Serializer):
    session = AIAgentSessionSerializer()
    reply = serializers.CharField()
    needs_project_confirmation = serializers.BooleanField()
    matched_project = serializers.DictField(allow_null=True)
    project_candidates = serializers.ListField()
    generated_testcases = TestCaseSerializer(many=True)
    executions = TestExecutionSerializer(many=True)
    auto_run = serializers.BooleanField()
