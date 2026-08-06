"""Recipe domain models -- Phase 1.

Matches docs/02-data-model.md. One simplification: the conceptual `RecipeTag` join entity isn't a
separate class since it carries no data of its own -- a standard Django ManyToManyField represents
the same relationship without extra code.

Enum values are English (code-level identifiers); the second element of each choice is the French
label shown in the UI -- the household using this app is French-speaking, only the codebase and
docs are in English.
"""

from django.db import models


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
