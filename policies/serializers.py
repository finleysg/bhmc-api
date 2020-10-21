from .models import Policy
from rest_framework import serializers


class PolicySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Policy
        fields = ("url", "id", "policy_type", "title", "description", )
