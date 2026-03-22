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
            'priority',
            'status',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_by', 'created_by_username', 'created_at', 'updated_at')