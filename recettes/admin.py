from django.contrib import admin

from .models import Etape, Ingredient, Recette, RecetteIngredient, Tag


class EtapeInline(admin.TabularInline):
    model = Etape
    extra = 1


class RecetteIngredientInline(admin.TabularInline):
    model = RecetteIngredient
    extra = 1


@admin.register(Recette)
class RecetteAdmin(admin.ModelAdmin):
    list_display = ["titre", "temps_preparation_min", "score_nutritionnel", "date_creation"]
    list_filter = ["score_nutritionnel", "tags"]
    search_fields = ["titre"]
    inlines = [RecetteIngredientInline, EtapeInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["nom", "unite_par_defaut", "categorie_rayon"]
    list_filter = ["categorie_rayon"]
    search_fields = ["nom"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["nom"]
