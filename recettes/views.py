import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import EtapeFormSet, RecetteForm, RecetteIngredientFormSet
from .models import Recette, Tag

NB_CANDIDATS_SURPRISE = 5


class ListeRecettesView(LoginRequiredMixin, ListView):
    model = Recette
    template_name = "recettes/liste.html"
    context_object_name = "recettes"
    paginate_by = 20

    def get_queryset(self):
        queryset = Recette.objects.prefetch_related("tags")
        recherche = self.request.GET.get("q")
        if recherche:
            queryset = queryset.filter(titre__icontains=recherche)
        tag_id = self.request.GET.get("tag")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.all()
        context["recherche"] = self.request.GET.get("q", "")
        context["tag_selectionne"] = self.request.GET.get("tag", "")
        context["score_choices"] = Recette.ScoreNutritionnel.choices
        return context


class DetailRecetteView(LoginRequiredMixin, DetailView):
    model = Recette
    template_name = "recettes/detail.html"
    context_object_name = "recette"

    def get_queryset(self):
        return Recette.objects.prefetch_related(
            "tags", "etapes", "recette_ingredients__ingredient"
        )


@login_required
def formulaire_recette(request, pk=None):
    recette = get_object_or_404(Recette, pk=pk) if pk else None

    if request.method == "POST":
        form = RecetteForm(request.POST, request.FILES, instance=recette)
        ingredients_formset = RecetteIngredientFormSet(
            request.POST, instance=recette, prefix="ingredients"
        )
        etapes_formset = EtapeFormSet(request.POST, instance=recette, prefix="etapes")

        if form.is_valid() and ingredients_formset.is_valid() and etapes_formset.is_valid():
            recette = form.save()
            ingredients_formset.instance = recette
            ingredients_formset.save()
            etapes_formset.instance = recette
            etapes_formset.save()
            return redirect("recettes:detail", pk=recette.pk)
    else:
        form = RecetteForm(instance=recette)
        ingredients_formset = RecetteIngredientFormSet(instance=recette, prefix="ingredients")
        etapes_formset = EtapeFormSet(instance=recette, prefix="etapes")

    return render(
        request,
        "recettes/formulaire.html",
        {
            "form": form,
            "ingredients_formset": ingredients_formset,
            "etapes_formset": etapes_formset,
            "recette": recette,
        },
    )


@login_required
@require_POST
def supprimer_recette(request, pk):
    recette = get_object_or_404(Recette, pk=pk)
    recette.delete()
    return redirect("recettes:liste")


@login_required
@require_POST
def marquer_cuisine(request, pk):
    recette = get_object_or_404(Recette, pk=pk)
    recette.derniere_cuisson_le = date.today()
    recette.save(update_fields=["derniere_cuisson_le"])
    return redirect("recettes:detail", pk=pk)


@login_required
def surprends_moi(request):
    queryset = Recette.objects.all()

    temps_max = request.GET.get("temps_max")
    if temps_max:
        queryset = queryset.filter(temps_preparation_min__lte=temps_max)

    score = request.GET.get("score_nutritionnel")
    if score:
        queryset = queryset.filter(score_nutritionnel=score)

    # Anti-répétition : privilégie les recettes jamais cuisinées ou cuisinées il y a longtemps,
    # sans exiger une seule "meilleure" réponse -- tirage au sort parmi les moins récentes.
    # nulls_first explicite : SQLite et PostgreSQL n'ordonnent pas les NULL de la même façon
    # par défaut, or les deux sont utilisés selon l'environnement (cf. docs/03-stack-technique.md).
    queryset = queryset.order_by(F("derniere_cuisson_le").asc(nulls_first=True))
    candidats = list(queryset[:NB_CANDIDATS_SURPRISE])

    if not candidats:
        messages.info(request, "Aucune recette ne correspond à ces critères.")
        return redirect("recettes:liste")

    recette = random.choice(candidats)
    return redirect("recettes:detail", pk=recette.pk)


@login_required
def ajouter_ligne_ingredient(request):
    index = int(request.GET.get("ingredients-TOTAL_FORMS", 0))
    formset = RecetteIngredientFormSet(prefix="ingredients")
    form = formset.empty_form
    form.prefix = formset.add_prefix(index)
    return render(
        request,
        "recettes/_ligne_ingredient.html",
        {"form": form, "next_total": index + 1},
    )


@login_required
def ajouter_ligne_etape(request):
    index = int(request.GET.get("etapes-TOTAL_FORMS", 0))
    formset = EtapeFormSet(prefix="etapes")
    form = formset.empty_form
    form.prefix = formset.add_prefix(index)
    return render(
        request,
        "recettes/_ligne_etape.html",
        {"form": form, "next_total": index + 1},
    )
