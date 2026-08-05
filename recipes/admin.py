from django.contrib import admin

from .models import Ingredient, Recipe, RecipeIngredient, Step, Tag


class StepInline(admin.TabularInline):
    model = Step
    extra = 1


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["title", "prep_time_min", "nutrition_score", "created_at"]
    list_filter = ["nutrition_score", "tags"]
    search_fields = ["title"]
    inlines = [RecipeIngredientInline, StepInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "default_unit", "aisle_category"]
    list_filter = ["aisle_category"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
