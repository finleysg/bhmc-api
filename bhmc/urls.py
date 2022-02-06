from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
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
router.register(r"settings", core_views.SeasonSettingsViewSet, "settings")
router.register(r"static-documents", document_views.StaticDocumentViewSet, "static-documents")
router.register(r"tags", content_views.TagViewSet, "tags")

urlpatterns = [
      path("admin/", admin.site.urls),
      path("api/", include(router.urls)),
      path("api/contact/", messaging_views.contact_message),
      path("api/clean-up/", register_views.cancel_expired),
      path("api/copy-event/<int:event_id>/", event_views.copy_event),
      path("api/random-photos/", document_views.random_photos),
      path("api/points/<int:season>/<category>/<int:top_n>/", damcup_views.get_top_points),
      path("api/friends/<int:player_id>/", register_views.friends),
      path("api/friends/add/<int:player_id>/", register_views.add_friend),
      path("api/friends/remove/<int:player_id>/", register_views.remove_friend),
      path("api/player-search/", register_views.player_search),
      path("api/hooks/stripe/", payment_views.payment_complete),
      path("api/import-handicaps/", register_views.import_handicaps),
      path("api/import-points/", damcup_views.import_points),
      path("api/import-scores/", damcup_views.import_scores),
      path("api/remove-card/<payment_method>", payment_views.remove_card),
      path("api/save-card/", payment_views.player_card),
      path("api/saved-cards/", payment_views.player_cards),
      path("api/payments/<int:payment_id>/confirm/", payment_views.confirm_payment),
      path("api/registration/<int:event_id>/create-slots/", register_views.create_event_slots),
      path("api/registration/<int:registration_id>/cancel/", register_views.cancel_reserved_slots),
      path("api/registration/<int:registration_id>/drop/", register_views.drop_players),
      path("api/registration/<int:registration_id>/move/", register_views.move_players),
      path("api/reports/event-report/<int:event_id>/", reporting_views.event_report),
      path("api/reports/membership/<int:season>/", reporting_views.membership_report),
      path("api/reports/payment-report/<int:event_id>/", reporting_views.payment_report),
      path("api/reports/skins-report/<int:event_id>/", reporting_views.skins_report),
      path("auth/", include("djoser.urls")),
      path("auth/", include("djoser.urls.authtoken")),
  ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
