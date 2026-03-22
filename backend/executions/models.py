from django.db import models

from projects.models import Project
from testcases.models import TestCase

class ExecutionLog(models.Model):
    class Level(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

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