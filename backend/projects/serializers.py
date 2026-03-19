from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'owner', 'owner_username', 'created_at')
        read_only_fields = ('owner', 'owner_username', 'created_at')
