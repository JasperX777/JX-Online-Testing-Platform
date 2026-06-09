from django.conf import settings
from django.db import models

from projects.models import Project
from testcases.models import TestCase


class TestExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='executions',
    )
    testcase = models.ForeignKey(
        TestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_executions',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    result_summary = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    failed_step_no = models.IntegerField(null=True, blank=True)
    current_step_no = models.IntegerField(null=True, blank=True)
    video_path = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.project_id}:{self.status}:{self.created_at}'


class ExecutionSchedule(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DISPATCHED = 'dispatched', 'Dispatched'
        CANCELLED = 'cancelled', 'Cancelled'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='execution_schedules',
    )
    testcase = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='execution_schedules',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='execution_schedules',
    )
    execution = models.OneToOneField(
        TestExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule',
    )
    scheduled_for = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_for']

    def __str__(self) -> str:
        return f'{self.project_id}:{self.testcase_id}:{self.scheduled_for}'


class ExecutionStepResult(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PASSED = 'passed', 'Passed'
        FAILED = 'failed', 'Failed'

    execution = models.ForeignKey(
        TestExecution,
        on_delete=models.CASCADE,
        related_name='step_results',
    )
    step_no = models.IntegerField()
    step_title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    action = models.CharField(max_length=50)
    target = models.CharField(max_length=255, blank=True)
    locator_type = models.CharField(max_length=20, blank=True, default='css')
    selector = models.CharField(max_length=255, blank=True)
    value = models.TextField(blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    executor_note = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    screenshot_path = models.CharField(max_length=500, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['step_no']

    def __str__(self) -> str:
        return f'{self.execution_id}:{self.step_no}:{self.status}'


class ExecutionLog(models.Model):
    class Level(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

    execution = models.ForeignKey(
        TestExecution,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    testcase = models.ForeignKey(
        TestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='execution_logs',
    )
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.INFO,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.project_id} : {self.level} : {self.created_at}'


class ExecutionReport(models.Model):
    execution = models.OneToOneField(
        TestExecution,
        on_delete=models.CASCADE,
        related_name='report',
    )
    report_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'report:{self.execution_id}'
