from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Profile

User = get_user_model()


class MeSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        user.profile.role = Profile.Role.USER
        user.profile.save(update_fields=['role'])
        return user
