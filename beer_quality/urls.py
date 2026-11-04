from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse_lazy
from quality.views import dashboard_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="quality/login.html",
            redirect_authenticated_user=True,
            next_page=reverse_lazy("dashboard"),
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page=reverse_lazy("login")),
        name="logout",
    ),
    path("", dashboard_view, name="dashboard"),
    path("quality/", include("quality.urls")),
]
