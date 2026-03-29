from rest_framework import serializers

from .models import ExecutionLog, TestExecution


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


class TestExecutionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)

    class Meta:
        model = TestExecution
        fields = (
            'id',
            'project',
            'project_name',
            'testcase',
            'testcase_title',
            'triggered_by',
            'triggered_by_username',
            'status',
            'exit_code',
            'result_summary',
            'started_at',
            'finished_at',
            'created_at',
        )
        read_only_fields = fields


class TestExecutionRunSerializer(serializers.Serializer):
    project = serializers.IntegerField()
    testcase = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        from projects.models import Project
        from testcases.models import TestCase

        project = Project.objects.filter(id=attrs['project']).first()
        if not project:
            raise serializers.ValidationError({'project': 'Project not found.'})

        testcase_id = attrs.get('testcase')
        testcase = None
        if testcase_id is not None:
            testcase = TestCase.objects.filter(id=testcase_id).first()
            if not testcase:
                raise serializers.ValidationError({'testcase': 'Test case not found.'})
            if testcase.project_id != project.id:
                raise serializers.ValidationError({'testcase': 'Test case does not belong to this project.'})

        attrs['project_obj'] = project
        attrs['testcase_obj'] = testcase
        return attrs
