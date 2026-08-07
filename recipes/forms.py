from django import forms
from django.forms import inlineformset_factory

from .models import Deal, Recipe, RecipeIngredient, StockItem, Step, Tag

DATE_INPUT = forms.DateInput(attrs={"type": "date"})


class RecipeForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Recipe
        fields = [
            "title",
            "description",
            "photo",
            "prep_time_min",
            "cook_time_min",
            "default_servings",
            "nutrition_score",
            "tags",
        ]


RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    fields=["ingredient", "quantity", "unit"],
    extra=1,
    can_delete=True,
)

StepFormSet = inlineformset_factory(
    Recipe,
    Step,
    fields=["order", "description"],
    extra=1,
    can_delete=True,
)


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ["ingredient", "store", "sale_price", "start_date", "end_date"]
        widgets = {
            "store": forms.TextInput(attrs={"placeholder": "Magasin (optionnel)"}),
            "sale_price": forms.NumberInput(attrs={"placeholder": "Prix promo (optionnel)"}),
            "start_date": DATE_INPUT,
            "end_date": DATE_INPUT,
        }


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = ["ingredient", "quantity", "unit", "location", "expiry_date"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"placeholder": "Quantité"}),
            "unit": forms.TextInput(attrs={"placeholder": "Unité"}),
            "expiry_date": DATE_INPUT,
        }
