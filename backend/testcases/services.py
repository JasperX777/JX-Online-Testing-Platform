from django.db import connection

from .models import TestCase


def filter_testcases(*, queryset, project_id=None, category=None, tag=None):
    qs = queryset

    if project_id:
        qs = qs.filter(project_id=project_id)
    if category:
        qs = qs.filter(category=category)
    if tag:
        if connection.vendor == 'sqlite':
            matching_ids = [obj.id for obj in qs if tag in (obj.tags or [])]
            qs = qs.filter(id__in=matching_ids)
        else:
            qs = qs.filter(tags__contains=[tag])

    return qs


def create_testcase(*, serializer, user):
    serializer.save(created_by=user)
