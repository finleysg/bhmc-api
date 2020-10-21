"""bhmc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework.routers import DefaultRouter

from core import views as core_views
from courses import views as course_views
from documents import views as document_views
from events import views as event_views
from messaging import views as messaging_views
from policies import views as policy_views
from register import views as register_views
from payments import views as payment_views

admin.site.site_header = "Bunker Hills Men's Club Administration"

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"courses", course_views.CourseViewSet, "courses")
router.register(r"documents", document_views.DocumentViewSet, "documents")
router.register(r"photos", document_views.PhotoViewSet, "photos")
router.register(r"events", event_views.EventViewSet, "events")
router.register(r"news", messaging_views.AnnouncementViewSet, "news")
router.register(r"policies", policy_views.PolicyViewSet, "policies")
router.register(r"payments", payment_views.PaymentViewSet, "payments")
router.register(r"players", register_views.PlayerViewSet, "players")
router.register(r"registration", register_views.RegistrationViewSet, "registration")
router.register(r"registration-slots", register_views.RegistrationSlotViewsSet, "registration-slots")

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    url(r"^api/", include(router.urls)),
    url(r"^api/settings/", core_views.current_settings),
    url(r'^auth/', include('djoser.urls')),
    url(r'^auth/', include('djoser.urls.authtoken')),
]
