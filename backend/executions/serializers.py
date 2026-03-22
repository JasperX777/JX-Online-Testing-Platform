from rest_framework import serializers
from .models import ExecutionLog


class ExecutionLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)

    class Meta:
        model = ExecutionLog
        fields = (
            'id',
            'project',
            'project_name',
            'testcase',
            'testcase_title',
            'level',
            'message',
            'created_at',
        )
