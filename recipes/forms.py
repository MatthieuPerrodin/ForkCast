from django import forms
from django.forms import inlineformset_factory

from .models import Deal, Recipe, RecipeIngredient, StockItem, Step, Tag


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
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class StockItemForm(forms.ModelForm):
    class Meta:
        model = StockItem
        fields = ["ingredient", "quantity", "unit", "location", "expiry_date"]
        widgets = {"expiry_date": forms.DateInput(attrs={"type": "date"})}
