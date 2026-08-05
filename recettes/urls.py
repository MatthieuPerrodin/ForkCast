from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "recettes"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="recettes/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.ListeRecettesView.as_view(), name="liste"),
    path("<int:pk>/", views.DetailRecetteView.as_view(), name="detail"),
]
