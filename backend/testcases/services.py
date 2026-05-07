from .models import TestCase


def filter_testcases(*, queryset, project_id=None, category=None, tag=None):
    qs = queryset

    if project_id:
        qs = qs.filter(project_id=project_id)
    if category:
        qs = qs.filter(category=category)
    if tag:
        qs = qs.filter(tags__contains=[tag])

    return qs


def create_testcase(*, serializer, user):
    serializer.save(created_by=user)
