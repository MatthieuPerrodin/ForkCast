from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import EtapeFormSet, RecetteForm, RecetteIngredientFormSet
from .models import Recette, Tag


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
