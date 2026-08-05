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
    path("nouvelle/", views.formulaire_recette, name="creer"),
    path("surprends-moi/", views.surprends_moi, name="surprends_moi"),
    path("ingredients/nouvelle-ligne/", views.ajouter_ligne_ingredient, name="ligne_ingredient"),
    path("etapes/nouvelle-ligne/", views.ajouter_ligne_etape, name="ligne_etape"),
    path("<int:pk>/", views.DetailRecetteView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.formulaire_recette, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer_recette, name="supprimer"),
    path("<int:pk>/cuisine/", views.marquer_cuisine, name="marquer_cuisine"),
]
