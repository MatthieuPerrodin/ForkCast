from django import forms
from django.forms import inlineformset_factory

from .models import Etape, Recette, RecetteIngredient, Tag


class RecetteForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Recette
        fields = [
            "titre",
            "description",
            "photo",
            "temps_preparation_min",
            "temps_cuisson_min",
            "portions_defaut",
            "score_nutritionnel",
            "tags",
        ]


RecetteIngredientFormSet = inlineformset_factory(
    Recette,
    RecetteIngredient,
    fields=["ingredient", "quantite", "unite"],
    extra=1,
    can_delete=True,
)

EtapeFormSet = inlineformset_factory(
    Recette,
    Etape,
    fields=["ordre", "description"],
    extra=1,
    can_delete=True,
)
