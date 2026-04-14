from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.authtoken import views as authtoken_views
from rest_framework.routers import DefaultRouter

from config.health import health
from config.openai_admin import redirect_openai_api_key_settings

from datasets.views import DatasetViewSet
from workspaces.views import WorkspaceViewSet
from analysis_runs.views import ChatAskView, ChatAskDetailView
from rag.views import RagIndexView, RagSearchView

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"datasets", DatasetViewSet, basename="dataset")

urlpatterns = [
    path("accounts/profile/", RedirectView.as_view(url="/app/", permanent=False)),
    path("accounts/login/", RedirectView.as_view(url="/app/login", permanent=False)),
    path("app/", include("enduser.urls")),
    # admin.site より前に登録（スーパーユーザーのみ。一覧は編集画面へリダイレクト）
    path(
        "admin/openai-api-key/",
        redirect_openai_api_key_settings,
        name="admin-openai-api-key",
    ),
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/auth/token/", authtoken_views.obtain_auth_token),
    path("api/v1/", include("table_intelligence.urls")),
    path("api/", include(router.urls)),
    path("api/chat/ask", ChatAskView.as_view()),
    path("api/chat/ask/<int:run_id>", ChatAskDetailView.as_view()),
    path("api/rag/index", RagIndexView.as_view()),
    path("api/rag/search", RagSearchView.as_view()),
    path("django-rq/", include("django_rq.urls")),
]
