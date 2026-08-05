from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "recipes"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="recipes/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.RecipeListView.as_view(), name="list"),
    path("new/", views.recipe_form, name="create"),
    path("surprise-me/", views.surprise_me, name="surprise_me"),
    path("ingredients/new-row/", views.add_ingredient_row, name="ingredient_row"),
    path("steps/new-row/", views.add_step_row, name="step_row"),
    path("<int:pk>/", views.RecipeDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.recipe_form, name="edit"),
    path("<int:pk>/delete/", views.delete_recipe, name="delete"),
    path("<int:pk>/cooked/", views.mark_cooked, name="mark_cooked"),
]
