from django.conf import settings
from django.db import models

class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TESTER = 'tester', 'Tester'
        DEVELOPER = 'developer', 'Developer'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DEVELOPER
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"