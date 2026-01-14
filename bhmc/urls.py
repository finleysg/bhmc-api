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
from scores import views as scoring_views

admin.site.site_header = "Bunker Hills Men's Club Administration"

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"aces", core_views.AceViewSet, "aces")
router.register(r"board", core_views.BoardMemberViewSet, "board")
router.register(r"champions", core_views.MajorChampionViewSet, "champions")
router.register(r"dam-cup", damcup_views.DamCupViewSet, "dam-cup")
router.register(r"low-scores", core_views.LowScoreViewSet, "low-scores")
router.register(r"courses", course_views.CourseViewSet, "courses")
router.register(r"tees", course_views.TeeViewSet, "tees")
router.register(r"documents", document_views.DocumentViewSet, "documents")
router.register(r"photos", document_views.PhotoViewSet, "photos")
router.register(r"events", event_views.EventViewSet, "events")
router.register(r"fee-types", event_views.FeeTypeViewSet, "fee-types")
router.register(r"tournament-results", event_views.TournamentResultViewSet, "tournament-results")
router.register(r"news", messaging_views.AnnouncementViewSet, "news")
router.register(r"policies", policy_views.PolicyViewSet, "policies")
router.register(r"page-content", content_views.PageContentViewSet, "page-content")
router.register(r"payments", payment_views.PaymentViewSet, "payments")
router.register(r"refunds", payment_views.RefundViewSet, "refunds")
router.register(r"players", register_views.PlayerViewSet, "players")
router.register(r"registration", register_views.RegistrationViewSet, "registration")
router.register(r"registration-fees", register_views.RegistrationFeeViewsSet, "registration-fees")
router.register(r"registration-slots", register_views.RegistrationSlotViewsSet, "registration-slots")
router.register(r"reports", reporting_views.ReportViewSet, "reports")
router.register(r"scores", scoring_views.EventScoreCardViewSet, "scores")
router.register(r"season-long-points", damcup_views.SeasonLongPointsViewSet, "season-long-points")
router.register(r"settings", core_views.SeasonSettingsViewSet, "settings")
router.register(r"static-documents", document_views.StaticDocumentViewSet, "static-documents")
router.register(r"tags", content_views.TagViewSet, "tags")

urlpatterns = [
      path("admin/", admin.site.urls),
      path("api/", include(router.urls)),
      path("api/contact/", messaging_views.contact_message),
      path("api/hooks/stripe/acacia/", payment_views.payment_complete_acacia),
      path("api/hooks/stripe/clover/", payment_views.payment_complete_clover),
      path("auth/", include("djoser.urls")),
      path("auth/token/login/", core_views.TokenCreateView.as_view(), name="login"),
      path("auth/token/logout/", core_views.TokenDestroyView.as_view(), name="logout"),
  ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
