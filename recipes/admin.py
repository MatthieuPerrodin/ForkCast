from django.contrib import admin

from .models import (
    Deal,
    Ingredient,
    MealSlot,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    ShoppingListItem,
    StockItem,
    Step,
    Tag,
)


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
    list_display = [
        "name", "default_unit", "aisle_category", "reference_quantity", "reference_price",
    ]
    list_filter = ["aisle_category"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(MealSlot)
class MealSlotAdmin(admin.ModelAdmin):
    list_display = ["date", "meal_time", "recipe", "planned_servings"]
    list_filter = ["meal_time"]
    list_select_related = ["recipe"]
    date_hierarchy = "date"


class ShoppingListItemInline(admin.TabularInline):
    model = ShoppingListItem
    extra = 0


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ["created_at"]
    inlines = [ShoppingListItemInline]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["ingredient", "store", "sale_price", "start_date", "end_date"]
    list_filter = ["store"]
    list_select_related = ["ingredient"]
    date_hierarchy = "start_date"


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["ingredient", "quantity", "unit", "location", "expiry_date"]
    list_filter = ["location"]
    list_select_related = ["ingredient"]
    date_hierarchy = "expiry_date"
