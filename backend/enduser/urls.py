from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from enduser import views

urlpatterns = [
    path("login", LoginView.as_view(template_name="enduser/login.html", redirect_authenticated_user=True), name="enduser-login"),
    path("logout", LogoutView.as_view(next_page="enduser-login"), name="enduser-logout"),
    path("", views.dashboard, name="enduser-dashboard"),
    path("datasets/new", views.dataset_new, name="enduser-dataset-new"),
    path("datasets/<int:dataset_id>/import/", views.dataset_import_confirm, name="enduser-dataset-import"),
    path("datasets/<int:dataset_id>/import", views.dataset_import_confirm),
    path("datasets/<int:dataset_id>", views.dataset_detail, name="enduser-dataset-detail"),
]
