from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Ingredient, MealSlot, Recipe, RecipeIngredient, Tag


class RecipesTestCase(TestCase):
    """Common fixtures: a logged-in user, one ingredient, one tag."""

    def setUp(self):
        User.objects.create_user(username="famille", password="testpass123")
        self.client.login(username="famille", password="testpass123")
        self.ingredient = Ingredient.objects.create(
            name="Riz", default_unit="g", aisle_category="pantry"
        )
        self.tag = Tag.objects.create(name="rapide")


class RecipeCRUDTests(RecipesTestCase):
    def test_login_required_for_list(self):
        self.client.logout()
        response = self.client.get(reverse("recipes:list"))
        self.assertEqual(response.status_code, 302)

    def test_create_recipe_with_ingredient_and_step(self):
        response = self.client.post(
            reverse("recipes:create"),
            {
                "title": "Riz sauté",
                "description": "Un classique.",
                "prep_time_min": 15,
                "cook_time_min": 10,
                "default_servings": 2,
                "nutrition_score": "balanced",
                "tags": [self.tag.pk],
                "ingredients-TOTAL_FORMS": 1,
                "ingredients-INITIAL_FORMS": 0,
                "ingredients-MIN_NUM_FORMS": 0,
                "ingredients-MAX_NUM_FORMS": 1000,
                "ingredients-0-ingredient": self.ingredient.pk,
                "ingredients-0-quantity": "200",
                "ingredients-0-unit": "g",
                "ingredients-0-id": "",
                "steps-TOTAL_FORMS": 1,
                "steps-INITIAL_FORMS": 0,
                "steps-MIN_NUM_FORMS": 0,
                "steps-MAX_NUM_FORMS": 1000,
                "steps-0-order": 1,
                "steps-0-description": "Cuire le riz.",
                "steps-0-id": "",
            },
        )
        recipe = Recipe.objects.get(title="Riz sauté")
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        self.assertEqual(recipe.recipe_ingredients.count(), 1)
        self.assertEqual(recipe.steps.count(), 1)

    def test_list_search_and_tag_filter(self):
        matching = Recipe.objects.create(title="Poulet rôti", prep_time_min=10)
        matching.tags.add(self.tag)
        Recipe.objects.create(title="Salade", prep_time_min=5)

        response = self.client.get(reverse("recipes:list"), {"q": "poulet"})
        self.assertContains(response, "Poulet rôti")
        self.assertNotContains(response, "Salade")

        response = self.client.get(reverse("recipes:list"), {"tag": self.tag.pk})
        self.assertContains(response, "Poulet rôti")
        self.assertNotContains(response, "Salade")

    def test_edit_recipe_updates_existing_ingredient_row(self):
        recipe = Recipe.objects.create(title="Riz", prep_time_min=10, default_servings=2)
        ri = RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        response = self.client.post(
            reverse("recipes:edit", args=[recipe.pk]),
            {
                "title": "Riz (modifié)",
                "description": "",
                "prep_time_min": 10,
                "cook_time_min": 0,
                "default_servings": 2,
                "nutrition_score": "balanced",
                "ingredients-TOTAL_FORMS": 1,
                "ingredients-INITIAL_FORMS": 1,
                "ingredients-MIN_NUM_FORMS": 0,
                "ingredients-MAX_NUM_FORMS": 1000,
                "ingredients-0-id": ri.pk,
                "ingredients-0-ingredient": self.ingredient.pk,
                "ingredients-0-quantity": "250",
                "ingredients-0-unit": "g",
                "steps-TOTAL_FORMS": 0,
                "steps-INITIAL_FORMS": 0,
                "steps-MIN_NUM_FORMS": 0,
                "steps-MAX_NUM_FORMS": 1000,
            },
        )
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        recipe.refresh_from_db()
        ri.refresh_from_db()
        self.assertEqual(recipe.title, "Riz (modifié)")
        self.assertEqual(ri.quantity, 250)

    def test_delete_recipe(self):
        recipe = Recipe.objects.create(title="À supprimer", prep_time_min=5)
        response = self.client.post(reverse("recipes:delete", args=[recipe.pk]))
        self.assertRedirects(response, reverse("recipes:list"))
        self.assertFalse(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_mark_cooked_sets_today(self):
        recipe = Recipe.objects.create(title="Riz", prep_time_min=5)
        response = self.client.post(reverse("recipes:mark_cooked", args=[recipe.pk]))
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        recipe.refresh_from_db()
        self.assertEqual(recipe.last_cooked_on, date.today())


class SurpriseMeTests(RecipesTestCase):
    def test_filters_by_prep_time(self):
        quick = Recipe.objects.create(title="Rapide", prep_time_min=10, nutrition_score="light")
        Recipe.objects.create(title="Long", prep_time_min=90, nutrition_score="hearty")

        response = self.client.get(reverse("recipes:surprise_me"), {"max_time": 15})
        self.assertRedirects(response, reverse("recipes:detail", args=[quick.pk]))

    def test_filters_by_nutrition_score(self):
        Recipe.objects.create(title="Rapide", prep_time_min=10, nutrition_score="light")
        hearty = Recipe.objects.create(title="Copieux", prep_time_min=20, nutrition_score="hearty")

        response = self.client.get(reverse("recipes:surprise_me"), {"nutrition_score": "hearty"})
        self.assertRedirects(response, reverse("recipes:detail", args=[hearty.pk]))

    def test_no_match_redirects_to_list(self):
        Recipe.objects.create(title="Long", prep_time_min=90)
        response = self.client.get(reverse("recipes:surprise_me"), {"max_time": 5})
        self.assertRedirects(response, reverse("recipes:list"))

    def test_anti_repetition_pool_does_not_crash_on_sqlite(self):
        # Regression check for the NULL-ordering bug documented in the journal: SQLite and
        # PostgreSQL sort NULL last_cooked_on differently by default. Mixing a never-cooked
        # recipe with a recently-cooked one exercises that ordering path.
        never_cooked = Recipe.objects.create(title="Jamais cuisinée", prep_time_min=10)
        recently = Recipe.objects.create(
            title="Cuisinée hier",
            prep_time_min=10,
            last_cooked_on=date.today() - timedelta(days=1),
        )
        response = self.client.get(reverse("recipes:surprise_me"), {"max_time": 15})
        self.assertIn(
            response.url,
            {
                reverse("recipes:detail", args=[never_cooked.pk]),
                reverse("recipes:detail", args=[recently.pk]),
            },
        )


class MealPlanningTests(RecipesTestCase):
    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(
            title="Carbonara", prep_time_min=10, default_servings=4
        )
        self.other_recipe = Recipe.objects.create(
            title="Salade", prep_time_min=5, default_servings=2
        )
        self.year, self.week, _ = date.today().isocalendar()
        self.monday = date.fromisocalendar(self.year, self.week, 1)
        self.week_url = reverse("recipes:planning_week", args=[self.year, self.week])

    def test_current_week_redirect(self):
        response = self.client.get(reverse("recipes:planning"))
        self.assertRedirects(response, self.week_url)

    def test_assign_recipe_to_slot(self):
        response = self.client.post(
            reverse("recipes:set_slot"),
            {
                "date": self.monday.isoformat(),
                "meal_time": "lunch",
                "recipe": self.recipe.pk,
                "planned_servings": 3,
                "next": self.week_url,
            },
        )
        self.assertRedirects(response, self.week_url)
        slot = MealSlot.objects.get(date=self.monday, meal_time="lunch")
        self.assertEqual(slot.recipe, self.recipe)
        self.assertEqual(slot.planned_servings, 3)

    def test_assigning_again_replaces_rather_than_duplicates(self):
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=self.recipe, planned_servings=4
        )
        self.client.post(
            reverse("recipes:set_slot"),
            {
                "date": self.monday.isoformat(),
                "meal_time": "lunch",
                "recipe": self.other_recipe.pk,
                "planned_servings": 2,
                "next": self.week_url,
            },
        )
        self.assertEqual(
            MealSlot.objects.filter(date=self.monday, meal_time="lunch").count(), 1
        )
        slot = MealSlot.objects.get(date=self.monday, meal_time="lunch")
        self.assertEqual(slot.recipe, self.other_recipe)

    def test_clear_slot(self):
        slot = MealSlot.objects.create(
            date=self.monday, meal_time="dinner", recipe=self.recipe, planned_servings=4
        )
        response = self.client.post(
            reverse("recipes:clear_slot", args=[slot.pk]), {"next": self.week_url}
        )
        self.assertRedirects(response, self.week_url)
        self.assertFalse(MealSlot.objects.filter(pk=slot.pk).exists())

    def test_week_view_shows_assigned_recipe(self):
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=self.recipe, planned_servings=3
        )
        response = self.client.get(self.week_url)
        self.assertContains(response, "Carbonara")
        self.assertContains(response, "3 portions")
