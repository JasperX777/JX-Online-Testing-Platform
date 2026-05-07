from rest_framework import serializers
from django.conf import settings

from .models import ExecutionLog, ExecutionReport, ExecutionStepResult, TestExecution


class ExecutionLogSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)

    class Meta:
        model = ExecutionLog
        fields = (
            'id',
            'execution',
            'project',
            'project_name',
            'testcase',
            'testcase_title',
            'level',
            'message',
            'created_at',
        )


class ExecutionReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionReport
        fields = (
            'id',
            'execution',
            'report_data',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class TestExecutionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)
    testcase_module = serializers.CharField(source='testcase.module', read_only=True)
    testcase_scenario = serializers.CharField(source='testcase.scenario', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)
    report = ExecutionReportSerializer(read_only=True)
    step_results = serializers.SerializerMethodField()

    class Meta:
        model = TestExecution
        fields = (
            'id',
            'project',
            'project_name',
            'testcase',
            'testcase_title',
            'testcase_module',
            'testcase_scenario',
            'triggered_by',
            'triggered_by_username',
            'status',
            'result_summary',
            'failure_reason',
            'failed_step_no',
            'current_step_no',
            'started_at',
            'finished_at',
            'created_at',
            'step_results',
            'report',
        )
        read_only_fields = fields

    def get_step_results(self, obj):
        return ExecutionStepResultSerializer(obj.step_results.all(), many=True).data


class ExecutionStepResultSerializer(serializers.ModelSerializer):
    screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionStepResult
        fields = (
            'id',
            'execution',
            'step_no',
            'step_title',
            'description',
            'action',
            'target',
            'locator_type',
            'selector',
            'value',
            'note',
            'status',
            'executor_note',
            'error_message',
            'screenshot_path',
            'screenshot_url',
            'executed_at',
        )
        read_only_fields = fields

    def get_screenshot_url(self, obj):
        if not obj.screenshot_path:
            return ''
        media_root = str(settings.MEDIA_ROOT)
        if obj.screenshot_path.startswith(media_root):
            relative_path = obj.screenshot_path[len(media_root):].lstrip('/\\')
            return f"{settings.MEDIA_URL}{relative_path.replace('\\', '/')}"
        return obj.screenshot_path


class TestExecutionRunSerializer(serializers.Serializer):
    project = serializers.IntegerField()
    testcase = serializers.IntegerField()

    def validate(self, attrs):
        from projects.models import Project
        from testcases.models import TestCase

        project = Project.objects.filter(id=attrs['project']).first()
        if not project:
            raise serializers.ValidationError({'project': 'Project not found.'})

        testcase = TestCase.objects.filter(id=attrs['testcase']).first()
        if not testcase:
            raise serializers.ValidationError({'testcase': 'Test case not found.'})
        if testcase.project_id != project.id:
            raise serializers.ValidationError({'testcase': 'Test case does not belong to this project.'})
        if not testcase.steps_json:
            raise serializers.ValidationError({'testcase': 'Test case requires at least one step.'})

        attrs['project_obj'] = project
        attrs['testcase_obj'] = testcase
        return attrs
