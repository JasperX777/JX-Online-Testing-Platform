from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class MeSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')