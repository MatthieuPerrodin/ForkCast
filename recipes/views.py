import random
from datetime import date, timedelta

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


def _recipes_on_deal_ids(ids=None):
    """Recipe pks using at least one ingredient with a currently active Deal. Pass `ids` to scope
    the check to a specific set of recipes (e.g. only the current page) instead of the whole table.
    """
    queryset = Recipe.objects.all()
    if ids is not None:
        queryset = queryset.filter(pk__in=ids)
    active_deal_ingredient_ids = Deal.objects.active().values_list("ingredient_id", flat=True)
    return set(
        queryset.filter(
            recipe_ingredients__ingredient_id__in=active_deal_ingredient_ids
        ).values_list("pk", flat=True)
    )


def _redirect_next(request, fallback):
    return redirect(request.POST.get("next") or fallback)


def _expiring_stock_suggestions():
    """Stock lots expiring within StockItem.EXPIRY_WARNING_DAYS (or already expired), each paired
    with one recipe using that ingredient if one exists -- surfaces "this expires soon, cook it"
    on the recipe list page. Small, bounded list in practice (a household's pantry rarely has more
    than a handful of lots expiring at once), so one query per item to find a suggestion is fine.
    """
    items = (
        StockItem.objects.filter(
            expiry_date__isnull=False,
            expiry_date__lte=date.today() + timedelta(days=StockItem.EXPIRY_WARNING_DAYS),
        )
        .select_related("ingredient")
        .order_by("expiry_date")
    )
    return [
        (item, Recipe.objects.filter(recipe_ingredients__ingredient=item.ingredient).first())
        for item in items
    ]


class RecipeListView(LoginRequiredMixin, ListView):
    model = Recipe
    template_name = "recipes/list.html"
    context_object_name = "recipes"
    paginate_by = 20

    #  GET param name -> Recipe field it filters on exactly (enum filters, all optional).
    ENUM_FILTERS = ["meal_moment", "cooking_mode", "difficulty", "estimated_cost"]

    def get_queryset(self):
        queryset = Recipe.objects.prefetch_related("tags")
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(title__icontains=search)
        # AND semantics: selecting both "vegetarian" and "gluten-free" should mean a recipe
        # satisfies both restrictions at once, not either one -- so each tag gets its own
        # .filter() call (its own join), rather than a single tags__id__in=[...] which would OR
        # them together on one join.
        for tag_id in self.request.GET.getlist("tag"):
            queryset = queryset.filter(tags__id=tag_id)
        for field in self.ENUM_FILTERS:
            value = self.request.GET.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.all()
        context["search"] = self.request.GET.get("q", "")
        context["selected_tags"] = self.request.GET.getlist("tag")
        context["nutrition_score_choices"] = Recipe.NutritionScore.choices
        context["meal_moment_choices"] = Recipe.MealMoment.choices
        context["cooking_mode_choices"] = Recipe.CookingMode.choices
        context["difficulty_choices"] = Recipe.Difficulty.choices
        context["estimated_cost_choices"] = Recipe.Cost.choices
        for field in self.ENUM_FILTERS:
            context[f"selected_{field}"] = self.request.GET.get(field, "")
        context["deal_recipe_ids"] = _recipes_on_deal_ids(
            ids=[r.pk for r in context["recipes"]]
        )
        context["expiring_stock"] = _expiring_stock_suggestions()
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
    for ri in recipe.recipe_ingredients.all():
        StockItem.objects.deduct_fifo(ri.ingredient_id, ri.unit, ri.quantity)
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

    # Anti-repetition, part 1: don't re-suggest a recipe already planned elsewhere this week --
    # last_cooked_on (below) only looks at cooking history, not the plan currently being built, so
    # without this a recipe could get suggested for both Tuesday and Friday dinner in one pass.
    iso_year, iso_week, _ = date.today().isocalendar()
    already_planned_ids = MealSlot.objects.filter(
        date__in=_week_dates(iso_year, iso_week)
    ).values_list("recipe_id", flat=True)
    queryset = queryset.exclude(pk__in=already_planned_ids)

    # Anti-repetition, part 2: favour recipes never cooked or cooked a long time ago, without
    # demanding a single "best" answer -- draw at random among the least recently cooked ones.
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
    return _redirect_next(request, "recipes:planning")


@login_required
@require_POST
def clear_slot(request, pk):
    get_object_or_404(MealSlot, pk=pk).delete()
    return _redirect_next(request, "recipes:planning")


@login_required
def shopping_list_view(request):
    shopping_list = ShoppingList.objects.current()
    items = shopping_list.items.select_related("ingredient") if shopping_list else []
    return render(
        request,
        "recipes/shopping_list.html",
        {"shopping_list": shopping_list, "items": items},
    )


@login_required
@require_POST
def generate_shopping_list(request, year, week):
    ShoppingList.generate_for_week(_week_dates(year, week))
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
    ShoppingListItem.objects.create(
        shopping_list=ShoppingList.objects.get_or_create_current(),
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
        {"form": form, "deals": Deal.objects.select_related("ingredient")},
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


def _add_formset_row(request, formset_class, prefix, template_name):
    index = int(request.GET.get(f"{prefix}-TOTAL_FORMS", 0))
    formset = formset_class(prefix=prefix)
    form = formset.empty_form
    form.prefix = formset.add_prefix(index)
    return render(request, template_name, {"form": form, "next_total": index + 1})


@login_required
def add_ingredient_row(request):
    return _add_formset_row(
        request, RecipeIngredientFormSet, "ingredients", "recipes/_ingredient_row.html"
    )


@login_required
def add_step_row(request):
    return _add_formset_row(request, StepFormSet, "steps", "recipes/_step_row.html")
