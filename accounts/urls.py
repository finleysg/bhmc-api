from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SkinTransactionViewSet, SkinViewSet, SkinSettingsViewSet
from .reports import SkinReportViewSet

router = DefaultRouter()
router.register(r'skin-transactions', SkinTransactionViewSet, basename='skin-transactions')
router.register(r'skins', SkinViewSet, basename='skins')
router.register(r'skin-settings', SkinSettingsViewSet, basename='skin-settings')
router.register(r'reports', SkinReportViewSet, basename='skin-reports')

urlpatterns = [
    path('', include(router.urls)),
]
