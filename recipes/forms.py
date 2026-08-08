from django import forms
from django.forms import inlineformset_factory

from .models import Deal, LongProcess, Recipe, RecipeIngredient, StockItem, Step, Tag

DATE_INPUT = forms.DateInput(attrs={"type": "date"})


MONTH_CHOICES = [
    ("1", "Janvier"), ("2", "Février"), ("3", "Mars"), ("4", "Avril"),
    ("5", "Mai"), ("6", "Juin"), ("7", "Juillet"), ("8", "Août"),
    ("9", "Septembre"), ("10", "Octobre"), ("11", "Novembre"), ("12", "Décembre"),
]


class RecipeForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )
    seasonality_months = forms.MultipleChoiceField(
        choices=MONTH_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Recipe
        fields = [
            "title",
            "description",
            "photo",
            "prep_time_min",
            "cook_time_min",
            "rest_time_min",
            "default_servings",
            "nutrition_score",
            "calories_kcal",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fridge_shelf_life_days",
            "is_freezable",
            "seasonality_months",
            "equipment_needed",
            "estimated_cost",
            "difficulty",
            "cooking_mode",
            "meal_moment",
            "notes",
            "tags",
        ]
        widgets = {
            "equipment_needed": forms.TextInput(
                attrs={"placeholder": "Ex : mixeur, robot culinaire (optionnel)"}
            ),
            "notes": forms.Textarea(
                attrs={"placeholder": "Remarques persos : la prochaine fois, moins de sel...", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # ModelForm.__init__ already populated self.initial from model_to_dict(), which for a
            # plain CharField model field is the raw "6,7,8" string -- and self.initial (the dict)
            # takes priority over field.initial when Django resolves what to render, so the dict
            # entry has to be the one fixed, not the field.
            self.initial["seasonality_months"] = [
                str(m) for m in self.instance.seasonality_month_list
            ]

    def clean_seasonality_months(self):
        return ",".join(self.cleaned_data.get("seasonality_months") or [])


RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    fields=["ingredient", "quantity", "unit", "state"],
    extra=1,
    can_delete=True,
    widgets={"state": forms.TextInput(attrs={"placeholder": "État (optionnel)"})},
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


class LongProcessForm(forms.ModelForm):
    class Meta:
        model = LongProcess
        fields = ["name", "kind", "started_on", "ready_on", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Nom (ex : levain de seigle)"}),
            "started_on": DATE_INPUT,
            "ready_on": DATE_INPUT,
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Notes (optionnel)"}),
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
