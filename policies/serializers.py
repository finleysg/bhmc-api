from .models import Policy
from rest_framework import serializers


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ("id", "policy_type", "title", "description", )
