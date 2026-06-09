from django.contrib import admin

from .models import ExecutionSchedule, TestExecution

admin.site.register(ExecutionSchedule)
admin.site.register(TestExecution)
