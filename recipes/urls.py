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
    path("import/", views.import_recipe, name="import_recipe"),
    path("surprise-me/", views.surprise_me, name="surprise_me"),
    path("leftover/", views.leftover_search, name="leftover_search"),
    path("planning/", views.planning_current, name="planning"),
    path("planning/<int:year>/W<int:week>/", views.planning_week, name="planning_week"),
    path("planning/slot/set/", views.set_slot, name="set_slot"),
    path("planning/slot/<int:pk>/clear/", views.clear_slot, name="clear_slot"),
    path("shopping-list/", views.shopping_list_view, name="shopping_list"),
    path(
        "shopping-list/generate/<int:year>/W<int:week>/",
        views.generate_shopping_list,
        name="generate_shopping_list",
    ),
    path("shopping-list/item/add/", views.add_shopping_item, name="add_shopping_item"),
    path(
        "shopping-list/item/<int:pk>/toggle/",
        views.toggle_shopping_item,
        name="toggle_shopping_item",
    ),
    path("deals/", views.deals_view, name="deals"),
    path("pantry/", views.pantry_view, name="pantry"),
    path("pantry/<int:pk>/edit/", views.edit_stock_item, name="edit_stock_item"),
    path("pantry/<int:pk>/delete/", views.delete_stock_item, name="delete_stock_item"),
    path("scan/", views.scan_view, name="scan"),
    path("scan/lookup/", views.scan_lookup, name="scan_lookup"),
    path("scan/add-to-pantry/", views.scan_add_to_pantry, name="scan_add_to_pantry"),
    path(
        "scan/add-to-shopping-list/",
        views.scan_add_to_shopping_list,
        name="scan_add_to_shopping_list",
    ),
    path("processes/", views.long_process_view, name="long_processes"),
    path("processes/<int:pk>/edit/", views.edit_long_process, name="edit_long_process"),
    path(
        "processes/<int:pk>/complete/",
        views.complete_long_process,
        name="complete_long_process",
    ),
    path("processes/<int:pk>/delete/", views.delete_long_process, name="delete_long_process"),
    path("ingredients/new-row/", views.add_ingredient_row, name="ingredient_row"),
    path("steps/new-row/", views.add_step_row, name="step_row"),
    path("<int:pk>/", views.RecipeDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.recipe_form, name="edit"),
    path("<int:pk>/delete/", views.delete_recipe, name="delete"),
    path("<int:pk>/cooked/", views.mark_cooked, name="mark_cooked"),
]
