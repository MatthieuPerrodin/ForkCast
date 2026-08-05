from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

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
