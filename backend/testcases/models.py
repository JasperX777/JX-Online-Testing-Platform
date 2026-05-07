from django.conf import settings
from django.db import models

from projects.models import Project


class TestCase(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        READY = 'ready', 'Ready'
        DEPRECATED = 'deprecated', 'Deprecated'

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_cases',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=100, blank=True)
    scenario = models.CharField(max_length=100, blank=True)
    steps_json = models.JSONField(default=list, blank=True)

    category = models.CharField(
        max_length=100,
        blank=True,
    )
    tags = models.JSONField(
        default=list,
        blank=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_test_cases',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.project_id} - {self.title}"
