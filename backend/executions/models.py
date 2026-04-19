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
    exit_code = models.IntegerField(null=True, blank=True)
    result_summary = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.project_id}:{self.status}:{self.created_at}'


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
