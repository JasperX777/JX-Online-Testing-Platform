from rest_framework import serializers

from .models import TestCase


class TestCaseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestCase
        fields = (
            'id',
            'project',
            'title',
            'description',
            'steps',
            'expected_result',
            'category',
            'tags',
            'test_type',
            'pytest_target',
            'priority',
            'status',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_by', 'created_by_username', 'created_at', 'updated_at')

    def validate_project(self, project):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if not user or not user.is_authenticated:
            return project

        if user.is_superuser or role == 'admin':
            return project

        if role == 'developer' and project.owner_id == user.id:
            return project

        raise serializers.ValidationError('You do not have permission to write test cases in this project.')
