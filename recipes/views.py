import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from .forms import DealForm, RecipeForm, RecipeIngredientFormSet, StepFormSet, StockItemForm
from .models import Deal, MealSlot, Recipe, ShoppingList, ShoppingListItem, StockItem, Tag

SURPRISE_CANDIDATE_POOL_SIZE = 5


def _recipes_on_deal_ids():
    """Recipe pks using at least one ingredient with a currently active Deal."""
    today = date.today()
    return set(
        Recipe.objects.filter(
            recipe_ingredients__ingredient__deals__start_date__lte=today,
            recipe_ingredients__ingredient__deals__end_date__gte=today,
        ).values_list("pk", flat=True)
    )


class RecipeListView(LoginRequiredMixin, ListView):
    model = Recipe
    template_name = "recipes/list.html"
    context_object_name = "recipes"
    paginate_by = 20

    def get_queryset(self):
        queryset = Recipe.objects.prefetch_related("tags")
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(title__icontains=search)
        tag_id = self.request.GET.get("tag")
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.all()
        context["search"] = self.request.GET.get("q", "")
        context["selected_tag"] = self.request.GET.get("tag", "")
        context["nutrition_score_choices"] = Recipe.NutritionScore.choices
        context["deal_recipe_ids"] = _recipes_on_deal_ids()
        return context


class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = "recipes/detail.html"
    context_object_name = "recipe"

    def get_queryset(self):
        return Recipe.objects.prefetch_related("tags", "steps", "recipe_ingredients__ingredient")


@login_required
def recipe_form(request, pk=None):
    recipe = get_object_or_404(Recipe, pk=pk) if pk else None

    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        ingredients_formset = RecipeIngredientFormSet(
            request.POST, instance=recipe, prefix="ingredients"
        )
        steps_formset = StepFormSet(request.POST, instance=recipe, prefix="steps")

        if form.is_valid() and ingredients_formset.is_valid() and steps_formset.is_valid():
            recipe = form.save()
            ingredients_formset.instance = recipe
            ingredients_formset.save()
            steps_formset.instance = recipe
            steps_formset.save()
            return redirect("recipes:detail", pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        ingredients_formset = RecipeIngredientFormSet(instance=recipe, prefix="ingredients")
        steps_formset = StepFormSet(instance=recipe, prefix="steps")

    return render(
        request,
        "recipes/form.html",
        {
            "form": form,
            "ingredients_formset": ingredients_formset,
            "steps_formset": steps_formset,
            "recipe": recipe,
        },
    )


@login_required
@require_POST
def delete_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe.delete()
    return redirect("recipes:list")


@login_required
@require_POST
def mark_cooked(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe.last_cooked_on = date.today()
    recipe.save(update_fields=["last_cooked_on"])
    return redirect("recipes:detail", pk=pk)


@login_required
def surprise_me(request):
    queryset = Recipe.objects.all()

    max_time = request.GET.get("max_time")
    if max_time:
        queryset = queryset.filter(prep_time_min__lte=max_time)

    score = request.GET.get("nutrition_score")
    if score:
        queryset = queryset.filter(nutrition_score=score)

    # Anti-repetition: favour recipes never cooked or cooked a long time ago, without demanding a
    # single "best" answer -- draw at random among the least recently cooked ones.
    # nulls_first is explicit: SQLite and PostgreSQL don't order NULLs the same way by default,
    # and both are used depending on the environment (see docs/03-tech-stack.md).
    queryset = queryset.order_by(F("last_cooked_on").asc(nulls_first=True))
    candidates = list(queryset[:SURPRISE_CANDIDATE_POOL_SIZE])

    if not candidates:
        messages.info(request, "Aucune recette ne correspond à ces critères.")
        return redirect("recipes:list")

    recipe = random.choice(candidates)
    return redirect("recipes:detail", pk=recipe.pk)


def _week_dates(year, week):
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(7)]


@login_required
def planning_current(request):
    iso_year, iso_week, _ = date.today().isocalendar()
    return redirect("recipes:planning_week", year=iso_year, week=iso_week)


@login_required
def planning_week(request, year, week):
    days = _week_dates(year, week)
    slots_by_key = {
        (slot.date, slot.meal_time): slot
        for slot in MealSlot.objects.filter(date__in=days).select_related("recipe")
    }

    grid = [
        {
            "date": day,
            "slots": [
                (meal_time, label, slots_by_key.get((day, meal_time)))
                for meal_time, label in MealSlot.MealTime.choices
            ],
        }
        for day in days
    ]

    prev_year, prev_week, _ = (days[0] - timedelta(days=7)).isocalendar()
    next_year, next_week, _ = (days[0] + timedelta(days=7)).isocalendar()

    return render(
        request,
        "recipes/planning.html",
        {
            "grid": grid,
            "year": year,
            "week": week,
            "week_start": days[0],
            "week_end": days[-1],
            "prev_year": prev_year,
            "prev_week": prev_week,
            "next_year": next_year,
            "next_week": next_week,
            "recipes": Recipe.objects.order_by("title"),
            "deal_recipe_ids": _recipes_on_deal_ids(),
        },
    )


@login_required
@require_POST
def set_slot(request):
    recipe = get_object_or_404(Recipe, pk=request.POST["recipe"])
    MealSlot.objects.update_or_create(
        date=request.POST["date"],
        meal_time=request.POST["meal_time"],
        defaults={
            "recipe": recipe,
            "planned_servings": request.POST.get("planned_servings") or recipe.default_servings,
        },
    )
    return redirect(request.POST.get("next") or "recipes:planning")


@login_required
@require_POST
def clear_slot(request, pk):
    slot = get_object_or_404(MealSlot, pk=pk)
    slot.delete()
    return redirect(request.POST.get("next") or "recipes:planning")


def _latest_shopping_list():
    return ShoppingList.objects.order_by("-created_at").first()


def _get_or_create_shopping_list():
    return _latest_shopping_list() or ShoppingList.objects.create()


@login_required
def shopping_list_view(request):
    shopping_list = _latest_shopping_list()
    items = shopping_list.items.select_related("ingredient") if shopping_list else []
    return render(
        request,
        "recipes/shopping_list.html",
        {"shopping_list": shopping_list, "items": items},
    )


@login_required
@require_POST
def generate_shopping_list(request, year, week):
    shopping_list = _get_or_create_shopping_list()
    shopping_list.items.filter(source=ShoppingListItem.Source.AUTO).delete()

    days = _week_dates(year, week)
    slots = MealSlot.objects.filter(date__in=days).select_related("recipe")

    # Aggregate by (ingredient, unit) -- no unit conversion (see docs/06-phase3-tasks.md), and
    # scale each recipe's quantities by planned_servings / default_servings, same idea as the
    # per-recipe portion adjuster from Phase 1.
    totals = {}
    for slot in slots:
        ratio = Decimal(slot.planned_servings) / Decimal(slot.recipe.default_servings)
        for ri in slot.recipe.recipe_ingredients.all():
            key = (ri.ingredient_id, ri.unit)
            totals[key] = totals.get(key, Decimal("0")) + ri.quantity * ratio

    for (ingredient_id, unit), quantity in totals.items():
        ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            ingredient_id=ingredient_id,
            unit=unit,
            quantity=quantity,
            source=ShoppingListItem.Source.AUTO,
        )

    return redirect("recipes:shopping_list")


@login_required
@require_POST
def toggle_shopping_item(request, pk):
    item = get_object_or_404(ShoppingListItem, pk=pk)
    item.checked = not item.checked
    item.save(update_fields=["checked"])
    return redirect("recipes:shopping_list")


@login_required
@require_POST
def add_shopping_item(request):
    shopping_list = _get_or_create_shopping_list()
    ShoppingListItem.objects.create(
        shopping_list=shopping_list,
        free_text_name=request.POST["free_text_name"],
        quantity=request.POST.get("quantity") or None,
        unit=request.POST.get("unit", ""),
        source=ShoppingListItem.Source.MANUAL,
    )
    return redirect("recipes:shopping_list")


@login_required
def deals_view(request):
    if request.method == "POST":
        form = DealForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("recipes:deals")
    else:
        form = DealForm()

    return render(
        request,
        "recipes/deals.html",
        {
            "form": form,
            "deals": Deal.objects.select_related("ingredient"),
            "today": date.today(),
        },
    )


@login_required
def pantry_view(request):
    if request.method == "POST":
        form = StockItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("recipes:pantry")
    else:
        form = StockItemForm()

    return render(
        request,
        "recipes/pantry.html",
        {"form": form, "stock_items": StockItem.objects.select_related("ingredient")},
    )


@login_required
def edit_stock_item(request, pk):
    item = get_object_or_404(StockItem, pk=pk)
    if request.method == "POST":
        form = StockItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("recipes:pantry")
    else:
        form = StockItemForm(instance=item)

    return render(request, "recipes/pantry_form.html", {"form": form, "item": item})


@login_required
@require_POST
def delete_stock_item(request, pk):
    get_object_or_404(StockItem, pk=pk).delete()
    return redirect("recipes:pantry")


@login_required
def add_ingredient_row(request):
    index = int(request.GET.get("ingredients-TOTAL_FORMS", 0))
    formset = RecipeIngredientFormSet(prefix="ingredients")
    form = formset.empty_form
    form.prefix = formset.add_prefix(index)
    return render(
        request,
        "recipes/_ingredient_row.html",
        {"form": form, "next_total": index + 1},
    )


@login_required
def add_step_row(request):
    index = int(request.GET.get("steps-TOTAL_FORMS", 0))
    formset = StepFormSet(prefix="steps")
    form = formset.empty_form
    form.prefix = formset.add_prefix(index)
    return render(
        request,
        "recipes/_step_row.html",
        {"form": form, "next_total": index + 1},
    )
