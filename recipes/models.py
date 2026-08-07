"""Recipe domain models -- Phases 1-3.

Matches docs/02-data-model.md. One simplification: the conceptual `RecipeTag` join entity isn't a
separate class since it carries no data of its own -- a standard Django ManyToManyField represents
the same relationship without extra code.

Enum values are English (code-level identifiers); the second element of each choice is the French
label shown in the UI -- the household using this app is French-speaking, only the codebase and
docs are in English.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import F, Sum


class Ingredient(models.Model):
    class AisleCategory(models.TextChoices):
        PRODUCE = "produce", "Fruits & légumes"
        PANTRY = "pantry", "Épicerie"
        FROZEN = "frozen", "Surgelés"
        DAIRY = "dairy", "Produits laitiers"
        MEAT_FISH = "meat_fish", "Viande & poisson"
        BEVERAGES = "beverages", "Boissons"
        OTHER = "other", "Autre"

    name = models.CharField(max_length=100, unique=True)
    default_unit = models.CharField(max_length=20)
    aisle_category = models.CharField(
        max_length=20, choices=AisleCategory.choices, default=AisleCategory.OTHER
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    class NutritionScore(models.TextChoices):
        LIGHT = "light", "Léger"
        BALANCED = "balanced", "Équilibré"
        HEARTY = "hearty", "Gourmand"

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="recipes/", blank=True, null=True)
    prep_time_min = models.PositiveIntegerField()
    cook_time_min = models.PositiveIntegerField(default=0, blank=True)
    default_servings = models.PositiveIntegerField(default=4)
    nutrition_score = models.CharField(
        max_length=20, choices=NutritionScore.choices, default=NutritionScore.BALANCED
    )
    last_cooked_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name="recipes", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Step(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="steps", on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    description = models.TextField()

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.recipe.title} - step {self.order}"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="recipe_ingredients", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=6, decimal_places=2)
    unit = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name}"


class MealSlot(models.Model):
    """A recipe assigned to a day + meal time. A slot only exists once assigned -- see
    docs/05-phase2-tasks.md for why "unplanned" is modeled as "no row" rather than a nullable FK.
    """

    class MealTime(models.TextChoices):
        LUNCH = "lunch", "Midi"
        DINNER = "dinner", "Soir"

    date = models.DateField()
    meal_time = models.CharField(max_length=10, choices=MealTime.choices)
    recipe = models.ForeignKey(Recipe, related_name="meal_slots", on_delete=models.CASCADE)
    planned_servings = models.PositiveIntegerField()

    class Meta:
        unique_together = ("date", "meal_time")
        ordering = ["date", "meal_time"]

    def __str__(self):
        return f"{self.date} {self.get_meal_time_display()} - {self.recipe.title}"


class ShoppingListQuerySet(models.QuerySet):
    def current(self):
        return self.order_by("-created_at").first()

    def get_or_create_current(self):
        return self.current() or self.create()


class ShoppingList(models.Model):
    """A single active list -- see docs/06-phase3-tasks.md for why this isn't a history of lists."""

    created_at = models.DateTimeField(auto_now_add=True)

    objects = ShoppingListQuerySet.as_manager()

    def __str__(self):
        return f"Liste du {self.created_at:%Y-%m-%d}"

    @classmethod
    def generate_for_week(cls, days):
        """Aggregates RecipeIngredients across the week's MealSlots, scaled by servings, reduced
        by available stock -- see docs/06-phase3-tasks.md and docs/07-phase4-tasks.md. Overwrites
        existing auto items on the active list; preserves manual ones and their checked state.
        """
        shopping_list = cls.objects.get_or_create_current()
        shopping_list.items.filter(source=ShoppingListItem.Source.AUTO).delete()

        slots = MealSlot.objects.filter(date__in=days).select_related("recipe").prefetch_related(
            "recipe__recipe_ingredients"
        )

        totals = defaultdict(lambda: Decimal("0"))
        for slot in slots:
            ratio = Decimal(slot.planned_servings) / Decimal(slot.recipe.default_servings)
            for ri in slot.recipe.recipe_ingredients.all():
                totals[(ri.ingredient_id, ri.unit)] += ri.quantity * ratio

        # One grouped query for all the stock on hand, rather than one query per ingredient.
        stock_by_key = defaultdict(lambda: Decimal("0"))
        stock_rows = (
            StockItem.objects.filter(ingredient_id__in={key[0] for key in totals})
            .values("ingredient_id", "unit")
            .annotate(total=Sum("quantity"))
        )
        for row in stock_rows:
            stock_by_key[(row["ingredient_id"], row["unit"])] = row["total"]

        for key, quantity in totals.items():
            remaining = quantity - stock_by_key[key]
            if remaining <= 0:
                continue
            ingredient_id, unit = key
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                ingredient_id=ingredient_id,
                unit=unit,
                quantity=remaining,
                source=ShoppingListItem.Source.AUTO,
            )

        return shopping_list


class ShoppingListItem(models.Model):
    class Source(models.TextChoices):
        AUTO = "auto", "Généré"
        MANUAL = "manual", "Ajouté manuellement"

    shopping_list = models.ForeignKey(ShoppingList, related_name="items", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(
        Ingredient, related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )
    free_text_name = models.CharField(max_length=150, blank=True)
    quantity = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    checked = models.BooleanField(default=False)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        ordering = ["ingredient__aisle_category", "id"]

    @property
    def display_name(self):
        return self.ingredient.name if self.ingredient else self.free_text_name

    @property
    def aisle_label(self):
        """Human-readable aisle for grouping the list in the template -- manually-added items
        with no ingredient reference don't have an aisle, so they get their own bucket."""
        return self.ingredient.get_aisle_category_display() if self.ingredient else "Autre"

    def __str__(self):
        return self.display_name


class DealQuerySet(models.QuerySet):
    def active(self, on_date=None):
        on_date = on_date or date.today()
        return self.filter(start_date__lte=on_date, end_date__gte=on_date)


class Deal(models.Model):
    """Manually-flagged discount on an ingredient -- Direction B V1, see requirements.md §5."""

    ingredient = models.ForeignKey(Ingredient, related_name="deals", on_delete=models.CASCADE)
    store = models.CharField(max_length=100, blank=True)
    sale_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    objects = DealQuerySet.as_manager()

    class Meta:
        ordering = ["-start_date"]

    def is_active(self, on_date=None):
        on_date = on_date or date.today()
        return self.start_date <= on_date <= self.end_date

    def __str__(self):
        return f"{self.ingredient.name} en rabais ({self.start_date} - {self.end_date})"


class StockItemQuerySet(models.QuerySet):
    def deduct_fifo(self, ingredient_id, unit, needed_quantity):
        """Best-effort: consumes the soonest-expiring lots first (the model's default ordering
        already sorts that way), stops once the need is covered or stock runs out -- doesn't
        error if stock is short.
        """
        remaining = needed_quantity
        for lot in self.filter(ingredient_id=ingredient_id, unit=unit):
            if remaining <= 0:
                break
            if lot.quantity <= remaining:
                remaining -= lot.quantity
                lot.delete()
            else:
                lot.quantity -= remaining
                lot.save(update_fields=["quantity"])
                remaining = Decimal("0")


class StockItem(models.Model):
    """One purchased lot of an ingredient in the pantry -- see docs/07-phase4-tasks.md for why
    this is per-lot rather than a running total (different lots expire at different times)."""

    class Location(models.TextChoices):
        PANTRY = "pantry", "Placard"
        FRIDGE = "fridge", "Frigo"
        FREEZER = "freezer", "Congélateur"

    EXPIRY_WARNING_DAYS = 3

    ingredient = models.ForeignKey(Ingredient, related_name="stock_items", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=7, decimal_places=2)
    unit = models.CharField(max_length=20)
    location = models.CharField(max_length=10, choices=Location.choices, default=Location.PANTRY)
    expiry_date = models.DateField(null=True, blank=True)
    added_on = models.DateField(auto_now_add=True)

    objects = StockItemQuerySet.as_manager()

    class Meta:
        ordering = [F("expiry_date").asc(nulls_last=True), "id"]

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        return self.expiry_date <= date.today() + timedelta(days=self.EXPIRY_WARNING_DAYS)

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < date.today())

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name} ({self.get_location_display()})"
