from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets

from .models import Policy
from .serializers import PolicySerializer


class PolicyViewSet(viewsets.ModelViewSet):

    serializer_class = PolicySerializer
    def get_queryset(self):
        queryset = Policy.objects.all()
        policy_type = self.request.query_params.get("policy_type", None)
        if policy_type is not None:
            queryset = queryset.filter(policy_type=policy_type)
        return queryset

    @method_decorator(cache_page(60 * 60 * 4))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
