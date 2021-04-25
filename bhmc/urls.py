"""bhmc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter

from core import views as core_views
from courses import views as course_views
from damcup import views as damcup_views
from documents import views as document_views
from events import views as event_views
from messaging import views as messaging_views
from policies import views as policy_views
from register import views as register_views
from payments import views as payment_views
from content import views as content_views
from reporting import views as reporting_views

admin.site.site_header = "Bunker Hills Men's Club Administration"

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"aces", core_views.AceViewSet, "aces")
router.register(r"board", core_views.BoardMemberViewSet, "board")
router.register(r"champions", core_views.MajorChampionViewSet, "champions")
router.register(r"dam-cup", damcup_views.DamCupViewSet, "dam-cup")
router.register(r"low-scores", core_views.LowScoreViewSet, "low-scores")
router.register(r"courses", course_views.CourseViewSet, "courses")
router.register(r"documents", document_views.DocumentViewSet, "documents")
router.register(r"photos", document_views.PhotoViewSet, "photos")
router.register(r"events", event_views.EventViewSet, "events")
router.register(r"fee-types", event_views.FeeTypeViewSet, "fee-types")
router.register(r"news", messaging_views.AnnouncementViewSet, "news")
router.register(r"policies", policy_views.PolicyViewSet, "policies")
router.register(r"page-content", content_views.PageContentViewSet, "page-content")
router.register(r"payments", payment_views.PaymentViewSet, "payments")
router.register(r"refunds", payment_views.RefundViewSet, "refunds")
router.register(r"players", register_views.PlayerViewSet, "players")
router.register(r"registration", register_views.RegistrationViewSet, "registration")
router.register(r"registration-fees", register_views.RegistrationFeeViewsSet, "registration-fees")
router.register(r"registration-slots", register_views.RegistrationSlotViewsSet, "registration-slots")
router.register(r"season-long-points", damcup_views.SeasonLongPointsViewSet, "season-long-points")
router.register(r"static-documents", document_views.StaticDocumentViewSet, "static-documents")

urlpatterns = [
      url(r"^admin/", admin.site.urls),
      url(r"^api/", include(router.urls)),
      url(r"^api/contact/$", messaging_views.contact_message),
      url(r"^api/copy-event/(?P<event_id>[0-9]+)/$", event_views.copy_event),
      url(r"^api/points/(?P<season>[0-9]+)/(?P<category>[a-z]+)/(?P<top_n>[0-9]+)/$", damcup_views.get_top_points),
      url(r"^api/friends/(?P<player_id>[0-9]+)/$", register_views.friends),
      url(r"^api/friends/add/(?P<player_id>[0-9]+)/$", register_views.add_friend),
      url(r"^api/friends/remove/(?P<player_id>[0-9]+)/$", register_views.remove_friend),
      url(r"^api/player-search/$", register_views.player_search),
      url(r"^api/hooks/stripe/$", payment_views.payment_complete),
      url(r"^api/import-points/$", damcup_views.import_points),
      url(r"^api/remove-card/(?P<payment_method>[-\w]+)/$", payment_views.remove_card),
      url(r"^api/save-card/$", payment_views.player_card),
      url(r"^api/saved-cards/$", payment_views.player_cards),
      url(r"^api/registration-expired/$", register_views.cancel_expired),
      url(r"^api/registration/(?P<registration_id>[0-9]+)/cancel/$", register_views.cancel_reserved_slots),
      url(r"^api/registration/(?P<registration_id>[0-9]+)/drop/$", register_views.drop_players),
      url(r"^api/registration/(?P<registration_id>[0-9]+)/move/$", register_views.move_players),
      url(r"^api/reports/event-report/(?P<event_id>[0-9]+)/$", reporting_views.event_report),
      url(r"^api/reports/payment-report/(?P<event_id>[0-9]+)/$", reporting_views.payment_report),
      url(r"^api/reports/skins-report/(?P<event_id>[0-9]+)/$", reporting_views.skins_report),
      url(r'^auth/', include('djoser.urls')),
      url(r'^auth/', include('djoser.urls.authtoken')),
  ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
