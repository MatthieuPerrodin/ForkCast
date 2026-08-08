import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Deal,
    Ingredient,
    MealSlot,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    ShoppingListItem,
    StockItem,
    Tag,
)
from .recipe_import import (
    RecipeImportError,
    import_recipe_from_url,
    parse_ingredient_line,
    parse_iso_duration_minutes,
    parse_servings,
)


class RecipesTestCase(TestCase):
    """Common fixtures: a logged-in user, one ingredient, one tag, and this week's ISO
    year/week/Monday -- several test classes need a real week to hang MealSlots off of."""

    def setUp(self):
        User.objects.create_user(username="famille", password="testpass123")
        self.client.login(username="famille", password="testpass123")
        self.ingredient = Ingredient.objects.create(
            name="Riz", default_unit="g", aisle_category="pantry"
        )
        self.tag = Tag.objects.create(name="rapide")
        self.year, self.week, _ = date.today().isocalendar()
        self.monday = date.fromisocalendar(self.year, self.week, 1)


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

    def test_list_multi_tag_filter_uses_and_semantics(self):
        gluten_free = Tag.objects.create(name="sans gluten")
        veggie_and_gf = Recipe.objects.create(title="Riz aux légumes", prep_time_min=15)
        veggie_and_gf.tags.add(self.tag, gluten_free)
        veggie_only = Recipe.objects.create(title="Pâtes végé", prep_time_min=15)
        veggie_only.tags.add(self.tag)

        # Selecting both tags should require both, not either -- a recipe missing one of the two
        # restrictions must not show up just because it matches the other.
        response = self.client.get(
            reverse("recipes:list"), {"tag": [self.tag.pk, gluten_free.pk]}
        )
        self.assertContains(response, "Riz aux légumes")
        self.assertNotContains(response, "Pâtes végé")

    def test_list_filters_by_metadata_enums(self):
        breakfast = Recipe.objects.create(
            title="Gruau",
            prep_time_min=5,
            meal_moment="breakfast",
            cooking_mode="no_cook",
            difficulty="easy",
            estimated_cost="low",
        )
        dinner = Recipe.objects.create(
            title="Rôti", prep_time_min=90, meal_moment="dinner", difficulty="hard"
        )

        response = self.client.get(reverse("recipes:list"), {"meal_moment": "breakfast"})
        self.assertContains(response, "Gruau")
        self.assertNotContains(response, "Rôti")

        response = self.client.get(reverse("recipes:list"), {"difficulty": "hard"})
        self.assertContains(response, "Rôti")
        self.assertNotContains(response, "Gruau")

        response = self.client.get(reverse("recipes:list"), {"cooking_mode": "no_cook"})
        self.assertContains(response, "Gruau")
        self.assertNotContains(response, "Rôti")

        response = self.client.get(reverse("recipes:list"), {"estimated_cost": "low"})
        self.assertContains(response, "Gruau")
        self.assertNotContains(response, "Rôti")

        response = self.client.get(reverse("recipes:list"))
        self.assertContains(response, breakfast.get_meal_moment_display())
        self.assertContains(response, dinner.get_difficulty_display())

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


class RecipeMetadataTests(RecipesTestCase):
    def test_create_recipe_with_full_metadata(self):
        response = self.client.post(
            reverse("recipes:create"),
            {
                "title": "Bol de poulet grillé",
                "description": "",
                "prep_time_min": 15,
                "cook_time_min": 20,
                "rest_time_min": 10,
                "default_servings": 2,
                "nutrition_score": "balanced",
                "calories_kcal": 550,
                "protein_g": "45.5",
                "carbs_g": "40.0",
                "fat_g": "15.0",
                "fridge_shelf_life_days": 3,
                "is_freezable": "on",
                "seasonality_months": ["6", "7", "8"],
                "equipment_needed": "Poêle, mixeur",
                "estimated_cost": "medium",
                "difficulty": "easy",
                "cooking_mode": "stovetop",
                "meal_moment": "dinner",
                "notes": "La prochaine fois, moins de sel.",
                "tags": [self.tag.pk],
                "ingredients-TOTAL_FORMS": 1,
                "ingredients-INITIAL_FORMS": 0,
                "ingredients-MIN_NUM_FORMS": 0,
                "ingredients-MAX_NUM_FORMS": 1000,
                "ingredients-0-ingredient": self.ingredient.pk,
                "ingredients-0-quantity": "200",
                "ingredients-0-unit": "g",
                "ingredients-0-state": "haché",
                "ingredients-0-id": "",
                "steps-TOTAL_FORMS": 0,
                "steps-INITIAL_FORMS": 0,
                "steps-MIN_NUM_FORMS": 0,
                "steps-MAX_NUM_FORMS": 1000,
            },
        )
        recipe = Recipe.objects.get(title="Bol de poulet grillé")
        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        self.assertEqual(recipe.rest_time_min, 10)
        self.assertEqual(recipe.calories_kcal, 550)
        self.assertEqual(recipe.protein_g, Decimal("45.5"))
        self.assertTrue(recipe.is_freezable)
        self.assertEqual(recipe.seasonality_months, "6,7,8")
        self.assertEqual(recipe.seasonality_month_list, [6, 7, 8])
        self.assertEqual(recipe.cooking_mode, "stovetop")
        self.assertEqual(recipe.meal_moment, "dinner")
        self.assertEqual(recipe.notes, "La prochaine fois, moins de sel.")
        ri = recipe.recipe_ingredients.get()
        self.assertEqual(ri.state, "haché")

    def test_edit_recipe_preselects_seasonality_checkboxes(self):
        recipe = Recipe.objects.create(
            title="Gaspacho", prep_time_min=15, seasonality_months="6,7,8"
        )
        response = self.client.get(reverse("recipes:edit", args=[recipe.pk]))
        form = response.context["form"]
        self.assertEqual(sorted(form.initial["seasonality_months"]), ["6", "7", "8"])

    def test_detail_page_shows_metadata_when_present(self):
        recipe = Recipe.objects.create(
            title="Bol de poulet grillé",
            prep_time_min=15,
            rest_time_min=10,
            fridge_shelf_life_days=3,
            is_freezable=True,
            seasonality_months="6,7,8",
            equipment_needed="Poêle, mixeur",
            calories_kcal=550,
            protein_g=Decimal("45.5"),
            estimated_cost="medium",
            difficulty="easy",
            cooking_mode="stovetop",
            meal_moment="dinner",
            notes="La prochaine fois, moins de sel.",
        )
        response = self.client.get(reverse("recipes:detail", args=[recipe.pk]))
        self.assertContains(response, "min de repos")
        self.assertContains(response, "Se congèle")
        self.assertContains(response, "Juin, Juil., Août")
        self.assertContains(response, "Poêle, mixeur")
        self.assertContains(response, "550 kcal")
        self.assertContains(response, recipe.get_meal_moment_display())
        self.assertContains(response, recipe.get_cooking_mode_display())
        self.assertContains(response, "La prochaine fois, moins de sel.")

    def test_detail_page_hides_metadata_sections_when_absent(self):
        recipe = Recipe.objects.create(title="Riz nature", prep_time_min=10)
        response = self.client.get(reverse("recipes:detail", args=[recipe.pk]))
        self.assertNotContains(response, "Infos pratiques")
        self.assertNotContains(response, "Nutrition (par portion)")
        self.assertNotContains(response, "Commentaires")


class ExpiryNotificationTests(RecipesTestCase):
    def test_expiring_item_shown_with_recipe_suggestion(self):
        recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        StockItem.objects.create(
            ingredient=self.ingredient, quantity=200, unit="g",
            expiry_date=date.today() + timedelta(days=2),
        )

        response = self.client.get(reverse("recipes:list"))
        self.assertContains(response, "Ça expire bientôt")
        self.assertContains(response, self.ingredient.name)
        self.assertContains(response, "cuisiner : Riz sauté")

    def test_item_not_expiring_soon_is_not_shown(self):
        StockItem.objects.create(
            ingredient=self.ingredient, quantity=200, unit="g",
            expiry_date=date.today() + timedelta(days=30),
        )
        response = self.client.get(reverse("recipes:list"))
        self.assertNotContains(response, "Ça expire bientôt")

    def test_already_expired_item_shown_as_perime(self):
        StockItem.objects.create(
            ingredient=self.ingredient, quantity=200, unit="g",
            expiry_date=date.today() - timedelta(days=1),
        )
        response = self.client.get(reverse("recipes:list"))
        self.assertContains(response, "périmé")

    def test_expiring_item_without_matching_recipe_has_no_suggestion_link(self):
        StockItem.objects.create(
            ingredient=self.ingredient, quantity=200, unit="g",
            expiry_date=date.today() + timedelta(days=1),
        )
        response = self.client.get(reverse("recipes:list"))
        self.assertContains(response, self.ingredient.name)
        self.assertNotContains(response, "cuisiner :")


class LeftoverSearchTests(RecipesTestCase):
    def test_lists_recipes_using_the_ingredient_without_a_quantity(self):
        matching = Recipe.objects.create(title="Riz sauté", prep_time_min=10, default_servings=4)
        RecipeIngredient.objects.create(
            recipe=matching, ingredient=self.ingredient, quantity=400, unit="g"
        )
        other_ingredient = Ingredient.objects.create(name="Pâtes", default_unit="g")
        other = Recipe.objects.create(title="Pâtes simples", prep_time_min=10)
        RecipeIngredient.objects.create(recipe=other, ingredient=other_ingredient, quantity=200, unit="g")

        response = self.client.get(reverse("recipes:leftover_search"), {"ingredient": self.ingredient.pk})
        self.assertContains(response, "Riz sauté")
        self.assertNotContains(response, "Pâtes simples")

    def test_excludes_recipe_when_leftover_cannot_cover_one_serving(self):
        recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10, default_servings=4)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=400, unit="g"
        )
        response = self.client.get(
            reverse("recipes:leftover_search"),
            {"ingredient": self.ingredient.pk, "quantity": "50", "unit": "g"},
        )
        self.assertNotContains(response, "Riz sauté")

    def test_includes_recipe_with_feasible_servings_count_when_leftover_is_enough(self):
        recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10, default_servings=4)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=400, unit="g"
        )
        response = self.client.get(
            reverse("recipes:leftover_search"),
            {"ingredient": self.ingredient.pk, "quantity": "150", "unit": "g"},
        )
        self.assertContains(response, "Riz sauté")
        self.assertContains(response, "1 portion")

    def test_unit_mismatch_ignores_quantity_and_still_shows_recipe(self):
        recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10, default_servings=4)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=400, unit="g"
        )
        response = self.client.get(
            reverse("recipes:leftover_search"),
            {"ingredient": self.ingredient.pk, "quantity": "1", "unit": "tasse"},
        )
        self.assertContains(response, "Riz sauté")


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

    def test_excludes_recipes_already_planned_this_week(self):
        already_planned = Recipe.objects.create(title="Déjà planifiée", prep_time_min=10)
        MealSlot.objects.create(
            date=self.monday, meal_time=MealSlot.MealTime.DINNER,
            recipe=already_planned, planned_servings=2,
        )
        free = Recipe.objects.create(title="Libre", prep_time_min=10)

        response = self.client.get(reverse("recipes:surprise_me"), {"max_time": 15})
        self.assertRedirects(response, reverse("recipes:detail", args=[free.pk]))

    def test_no_unplanned_recipe_left_this_week_falls_back_to_message(self):
        only_recipe = Recipe.objects.create(title="Seule recette", prep_time_min=10)
        MealSlot.objects.create(
            date=self.monday, meal_time=MealSlot.MealTime.LUNCH,
            recipe=only_recipe, planned_servings=2,
        )
        response = self.client.get(reverse("recipes:surprise_me"), {"max_time": 15})
        self.assertRedirects(response, reverse("recipes:list"))


class MealPlanningTests(RecipesTestCase):
    def setUp(self):
        super().setUp()
        self.recipe = Recipe.objects.create(
            title="Carbonara", prep_time_min=10, default_servings=4
        )
        self.other_recipe = Recipe.objects.create(
            title="Salade", prep_time_min=5, default_servings=2
        )
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


class ShoppingListTests(RecipesTestCase):
    def setUp(self):
        super().setUp()
        self.tuesday = self.monday + timedelta(days=1)
        self.generate_url = reverse(
            "recipes:generate_shopping_list", args=[self.year, self.week]
        )

    def test_generate_aggregates_same_ingredient_and_unit_across_recipes(self):
        recipe_a = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe_a, ingredient=self.ingredient, quantity=100, unit="g"
        )
        recipe_b = Recipe.objects.create(title="B", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe_b, ingredient=self.ingredient, quantity=50, unit="g"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe_a, planned_servings=2
        )
        MealSlot.objects.create(
            date=self.tuesday, meal_time="dinner", recipe=recipe_b, planned_servings=2
        )

        response = self.client.post(self.generate_url)
        self.assertRedirects(response, reverse("recipes:shopping_list"))

        item = ShoppingListItem.objects.get(ingredient=self.ingredient, unit="g")
        self.assertEqual(item.quantity, Decimal("150.00"))
        self.assertEqual(item.source, ShoppingListItem.Source.AUTO)

    def test_generate_scales_by_planned_servings(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=4)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )

        self.client.post(self.generate_url)

        item = ShoppingListItem.objects.get(ingredient=self.ingredient)
        self.assertEqual(item.quantity, Decimal("50.00"))  # 100 * (2/4)

    def test_generate_keeps_different_units_separate(self):
        recipe_a = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe_a, ingredient=self.ingredient, quantity=100, unit="g"
        )
        recipe_b = Recipe.objects.create(title="B", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe_b, ingredient=self.ingredient, quantity=1, unit="tasse"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe_a, planned_servings=2
        )
        MealSlot.objects.create(
            date=self.tuesday, meal_time="dinner", recipe=recipe_b, planned_servings=2
        )

        self.client.post(self.generate_url)

        self.assertEqual(
            ShoppingListItem.objects.filter(ingredient=self.ingredient).count(), 2
        )

    def test_regenerate_overwrites_auto_but_preserves_manual_and_checked(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )

        self.client.post(self.generate_url)
        auto_item = ShoppingListItem.objects.get(source=ShoppingListItem.Source.AUTO)
        auto_item.checked = True
        auto_item.save()

        self.client.post(
            reverse("recipes:add_shopping_item"),
            {"free_text_name": "Papier essuie-tout", "quantity": "", "unit": ""},
        )
        manual_item = ShoppingListItem.objects.get(source=ShoppingListItem.Source.MANUAL)
        manual_item.checked = True
        manual_item.save()

        self.client.post(self.generate_url)

        self.assertEqual(
            ShoppingListItem.objects.filter(source=ShoppingListItem.Source.AUTO).count(), 1
        )
        new_auto_item = ShoppingListItem.objects.get(source=ShoppingListItem.Source.AUTO)
        self.assertFalse(new_auto_item.checked)

        manual_item.refresh_from_db()
        self.assertTrue(manual_item.checked)
        self.assertEqual(manual_item.display_name, "Papier essuie-tout")

    def test_toggle_checked(self):
        shopping_list = ShoppingList.objects.create()
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=self.ingredient, quantity=100, unit="g"
        )
        response = self.client.post(reverse("recipes:toggle_shopping_item", args=[item.pk]))
        self.assertRedirects(response, reverse("recipes:shopping_list"))
        item.refresh_from_db()
        self.assertTrue(item.checked)

    def test_add_manual_item(self):
        response = self.client.post(
            reverse("recipes:add_shopping_item"),
            {"free_text_name": "Sacs poubelle", "quantity": "2", "unit": "boîtes"},
        )
        self.assertRedirects(response, reverse("recipes:shopping_list"))
        item = ShoppingListItem.objects.get(free_text_name="Sacs poubelle")
        self.assertEqual(item.source, ShoppingListItem.Source.MANUAL)
        self.assertEqual(item.quantity, Decimal("2"))


class CostEstimateTests(RecipesTestCase):
    def test_unit_price_requires_both_reference_fields(self):
        self.assertIsNone(self.ingredient.unit_price)
        self.ingredient.reference_quantity = Decimal("1000")
        self.assertIsNone(self.ingredient.unit_price)
        self.ingredient.reference_price = Decimal("4.99")
        self.assertEqual(self.ingredient.unit_price, Decimal("4.99") / Decimal("1000"))

    def test_line_cost_estimated_when_unit_matches(self):
        self.ingredient.reference_quantity = Decimal("1000")
        self.ingredient.reference_price = Decimal("5.00")
        self.ingredient.save()
        shopping_list = ShoppingList.objects.create()
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=self.ingredient, quantity=200, unit="g",
        )
        self.assertEqual(item.estimated_cost, Decimal("1.00"))

    def test_line_cost_none_when_unit_does_not_match_default_unit(self):
        self.ingredient.reference_quantity = Decimal("1000")
        self.ingredient.reference_price = Decimal("5.00")
        self.ingredient.save()
        shopping_list = ShoppingList.objects.create()
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=self.ingredient, quantity=1, unit="kg",
        )
        self.assertIsNone(item.estimated_cost)

    def test_line_cost_none_for_manual_item_without_ingredient(self):
        shopping_list = ShoppingList.objects.create()
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list, free_text_name="Sacs poubelle", quantity=2, unit="boîtes",
        )
        self.assertIsNone(item.estimated_cost)

    def test_shopping_list_total_sums_only_priced_items(self):
        self.ingredient.reference_quantity = Decimal("1000")
        self.ingredient.reference_price = Decimal("5.00")
        self.ingredient.save()
        unpriced_ingredient = Ingredient.objects.create(name="Sel", default_unit="g")
        shopping_list = ShoppingList.objects.create()
        ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=self.ingredient, quantity=200, unit="g",
        )
        ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=unpriced_ingredient, quantity=50, unit="g",
        )
        self.assertEqual(shopping_list.estimated_total, Decimal("1.00"))

    def test_estimated_total_shown_on_shopping_list_page(self):
        self.ingredient.reference_quantity = Decimal("1000")
        self.ingredient.reference_price = Decimal("5.00")
        self.ingredient.save()
        shopping_list = ShoppingList.objects.create()
        ShoppingListItem.objects.create(
            shopping_list=shopping_list, ingredient=self.ingredient, quantity=200, unit="g",
        )
        response = self.client.get(reverse("recipes:shopping_list"))
        self.assertContains(response, "Coût estimé")


def _json_ld_page(payload):
    return (
        "<html><head><script type=\"application/ld+json\">"
        + json.dumps(payload)
        + "</script></head><body>Hello</body></html>"
    )


class RecipeImportParsingTests(TestCase):
    """Pure parsing, no HTTP -- the messy real-world shapes schema.org allows for the same data."""

    def test_iso_duration_parsing(self):
        self.assertEqual(parse_iso_duration_minutes("PT30M"), 30)
        self.assertEqual(parse_iso_duration_minutes("PT1H30M"), 90)
        self.assertEqual(parse_iso_duration_minutes("PT2H"), 120)
        self.assertIsNone(parse_iso_duration_minutes("bogus"))
        self.assertIsNone(parse_iso_duration_minutes(None))

    def test_servings_parsing_handles_text_and_lists(self):
        self.assertEqual(parse_servings("4 portions"), 4)
        self.assertEqual(parse_servings(["6 servings"]), 6)
        self.assertEqual(parse_servings(6), 6)
        self.assertIsNone(parse_servings("quelques"))

    def test_ingredient_line_splits_quantity_unit_and_name(self):
        self.assertEqual(parse_ingredient_line("400 g de spaghetti"),
                         (Decimal("400"), "g", "spaghetti"))
        self.assertEqual(parse_ingredient_line("2 cups flour"),
                         (Decimal("2"), "cups", "flour"))

    def test_ingredient_line_treats_non_unit_word_as_part_of_the_name(self):
        # "oeufs" isn't a unit -- it must not be swallowed as one, leaving an empty name.
        quantity, unit, name = parse_ingredient_line("3 oeufs frais")
        self.assertEqual(quantity, Decimal("3"))
        self.assertEqual(unit, "")
        self.assertEqual(name, "oeufs frais")

    def test_ingredient_line_without_quantity_keeps_whole_text_as_name(self):
        self.assertEqual(parse_ingredient_line("Sel et poivre"), (None, "", "Sel et poivre"))

    @patch("recipes.recipe_import._fetch_html")
    def test_import_reads_graph_wrapped_recipe(self, mock_fetch):
        # @graph wrappers are common (Yoast and similar) -- the Recipe is nested, not top level.
        mock_fetch.return_value = _json_ld_page({
            "@graph": [
                {"@type": "WebSite", "name": "Un site"},
                {
                    "@type": "Recipe",
                    "name": "Carbonara",
                    "description": "<p>La <b>vraie</b> recette</p>",
                    "prepTime": "PT10M",
                    "cookTime": "PT15M",
                    "recipeYield": "4 portions",
                    "recipeIngredient": ["400 g de spaghetti", "3 oeufs"],
                    "recipeInstructions": [
                        {"@type": "HowToStep", "text": "Cuire les pâtes."},
                        {"@type": "HowToStep", "text": "Mélanger."},
                    ],
                },
            ]
        })
        draft = import_recipe_from_url("https://exemple.com/carbonara")
        self.assertEqual(draft["title"], "Carbonara")
        self.assertEqual(draft["description"], "La vraie recette")  # HTML stripped
        self.assertEqual(draft["prep_time_min"], 10)
        self.assertEqual(draft["cook_time_min"], 15)
        self.assertEqual(draft["default_servings"], 4)
        self.assertEqual(draft["steps"], ["Cuire les pâtes.", "Mélanger."])
        self.assertEqual(draft["ingredients"][0], (Decimal("400"), "g", "spaghetti"))

    @patch("recipes.recipe_import._fetch_html")
    def test_import_reads_type_list_and_string_instructions(self, mock_fetch):
        mock_fetch.return_value = _json_ld_page({
            "@type": ["Recipe", "NewsArticle"],
            "name": "Salade",
            "recipeIngredient": "1 laitue",
            "recipeInstructions": "Laver.\nCouper.",
        })
        draft = import_recipe_from_url("https://exemple.com/salade")
        self.assertEqual(draft["title"], "Salade")
        self.assertEqual(draft["steps"], ["Laver.", "Couper."])
        self.assertEqual(len(draft["ingredients"]), 1)

    @patch("recipes.recipe_import._fetch_html")
    def test_import_raises_when_page_has_no_recipe(self, mock_fetch):
        mock_fetch.return_value = _json_ld_page({"@type": "WebSite", "name": "Un site"})
        with self.assertRaises(RecipeImportError):
            import_recipe_from_url("https://exemple.com/pas-une-recette")

    @patch("recipes.recipe_import._fetch_html")
    def test_import_ignores_malformed_json_ld_blocks(self, mock_fetch):
        mock_fetch.return_value = (
            '<script type="application/ld+json">{ not json </script>'
            + _json_ld_page({"@type": "Recipe", "name": "Quand même trouvée"})
        )
        self.assertEqual(
            import_recipe_from_url("https://exemple.com/x")["title"], "Quand même trouvée"
        )

    def test_import_rejects_non_http_scheme(self):
        with self.assertRaises(RecipeImportError):
            import_recipe_from_url("file:///etc/passwd")


class RecipeImportViewTests(RecipesTestCase):
    @patch("recipes.views.import_recipe_from_url")
    def test_import_prefills_the_create_form_without_saving(self, mock_import):
        mock_import.return_value = {
            "title": "Carbonara importée",
            "description": "Une description",
            "prep_time_min": 10,
            "cook_time_min": 15,
            "default_servings": 4,
            "ingredients": [(Decimal("400"), "g", "spaghetti")],
            "steps": ["Cuire les pâtes."],
            "source_url": "https://exemple.com/carbonara",
        }
        response = self.client.post(reverse("recipes:import_recipe"), {"url": "https://x.com/r"})
        self.assertContains(response, "Carbonara importée")
        self.assertContains(response, "Cuire les pâtes.")
        self.assertContains(response, "rien n'est encore sauvegardé")
        # Nothing committed: the user still has to submit the create form.
        self.assertFalse(Recipe.objects.filter(title="Carbonara importée").exists())

    @patch("recipes.views.import_recipe_from_url", side_effect=RecipeImportError("Pas trouvé"))
    def test_import_shows_error_without_crashing(self, mock_import):
        response = self.client.post(reverse("recipes:import_recipe"), {"url": "https://x.com/r"})
        self.assertContains(response, "Pas trouvé")
        self.assertEqual(response.status_code, 200)


class ScanTests(RecipesTestCase):
    def test_scan_page_offers_camera_and_keeps_typed_fallback(self):
        """The camera reader is progressive enhancement -- the typed barcode field must stay on
        the page so a device with no camera (or refused permission) can still use the lookup."""
        response = self.client.get(reverse("recipes:scan"))
        self.assertContains(response, "Scanner avec la caméra")
        self.assertContains(response, "html5-qrcode")
        self.assertContains(response, 'name="barcode"')
        # Django's {# #} comment syntax is single-line only; a multi-line one renders as visible
        # page text instead (caught on this page during review).
        self.assertNotContains(response, "{#")

    def _mock_off_response(self, payload):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_response
        return mock_context

    @patch("recipes.views.urllib.request.urlopen")
    def test_scan_lookup_shows_product_when_found(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_off_response(
            {"status": 1, "product": {"product_name": "Nutella", "quantity": "400 g"}}
        )
        response = self.client.get(reverse("recipes:scan_lookup"), {"barcode": "3017620422003"})
        self.assertContains(response, "Nutella")
        self.assertContains(response, "Ajouter au garde-manger")
        self.assertContains(response, "Ajouter à la liste de courses")

    @patch("recipes.views.urllib.request.urlopen")
    def test_scan_lookup_shows_not_found_when_off_has_no_match(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_off_response({"status": 0})
        response = self.client.get(reverse("recipes:scan_lookup"), {"barcode": "0000000000000"})
        self.assertContains(response, "non trouvé")

    @patch("recipes.views.urllib.request.urlopen")
    def test_scan_lookup_shows_not_found_when_product_has_no_name(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_off_response(
            {"status": 1, "product": {"product_name": "", "quantity": "400 g"}}
        )
        response = self.client.get(reverse("recipes:scan_lookup"), {"barcode": "123"})
        self.assertContains(response, "non trouvé")

    @patch("recipes.views.urllib.request.urlopen", side_effect=URLError("boom"))
    def test_scan_lookup_degrades_gracefully_on_network_error(self, mock_urlopen):
        response = self.client.get(reverse("recipes:scan_lookup"), {"barcode": "123"})
        self.assertContains(response, "non trouvé")

    def test_scan_add_to_pantry_creates_ingredient_and_stock_item(self):
        response = self.client.post(
            reverse("recipes:scan_add_to_pantry"),
            {"product_name": "Nutella", "quantity": "400", "unit": "g"},
        )
        self.assertRedirects(response, reverse("recipes:pantry"))
        ingredient = Ingredient.objects.get(name="Nutella")
        item = StockItem.objects.get(ingredient=ingredient)
        self.assertEqual(item.quantity, Decimal("400"))
        self.assertEqual(item.unit, "g")

    def test_scan_add_to_pantry_reuses_existing_ingredient_with_matching_name(self):
        Ingredient.objects.create(name="Nutella", default_unit="g")
        self.client.post(
            reverse("recipes:scan_add_to_pantry"),
            {"product_name": "Nutella", "quantity": "400", "unit": "g"},
        )
        self.assertEqual(Ingredient.objects.filter(name="Nutella").count(), 1)

    def test_scan_add_to_shopping_list_creates_free_text_item(self):
        response = self.client.post(
            reverse("recipes:scan_add_to_shopping_list"),
            {"product_name": "Nutella", "quantity": "400", "unit": "g"},
        )
        self.assertRedirects(response, reverse("recipes:shopping_list"))
        item = ShoppingListItem.objects.get(free_text_name="Nutella")
        self.assertIsNone(item.ingredient)


class DealTests(RecipesTestCase):
    def test_is_active_on_boundary_dates(self):
        deal = Deal.objects.create(
            ingredient=self.ingredient,
            start_date=date.today(),
            end_date=date.today(),
        )
        self.assertTrue(deal.is_active())
        self.assertTrue(deal.is_active(on_date=date.today()))
        self.assertFalse(deal.is_active(on_date=date.today() - timedelta(days=1)))
        self.assertFalse(deal.is_active(on_date=date.today() + timedelta(days=1)))

    def test_create_deal_via_form(self):
        response = self.client.post(
            reverse("recipes:deals"),
            {
                "ingredient": self.ingredient.pk,
                "store": "IGA",
                "sale_price": "3.99",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=6)).isoformat(),
            },
        )
        self.assertRedirects(response, reverse("recipes:deals"))
        self.assertTrue(Deal.objects.filter(ingredient=self.ingredient, store="IGA").exists())

    def test_recipe_using_deal_ingredient_is_flagged_on_list_and_planning(self):
        on_sale_recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=on_sale_recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        other_ingredient = Ingredient.objects.create(name="Pâtes", default_unit="g")
        other_recipe = Recipe.objects.create(title="Pâtes simples", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=other_recipe, ingredient=other_ingredient, quantity=100, unit="g"
        )
        Deal.objects.create(
            ingredient=self.ingredient,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )

        response = self.client.get(reverse("recipes:list"))
        self.assertIn(on_sale_recipe.pk, response.context["deal_recipe_ids"])
        self.assertNotIn(other_recipe.pk, response.context["deal_recipe_ids"])
        self.assertContains(response, "rabais")

        response = self.client.get(reverse("recipes:planning_week", args=[self.year, self.week]))
        self.assertIn(on_sale_recipe.pk, response.context["deal_recipe_ids"])

    def test_expired_deal_does_not_flag_recipe(self):
        recipe = Recipe.objects.create(title="Riz sauté", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        Deal.objects.create(
            ingredient=self.ingredient,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
        )

        response = self.client.get(reverse("recipes:list"))
        self.assertNotIn(recipe.pk, response.context["deal_recipe_ids"])


class PantryTests(RecipesTestCase):
    def test_add_stock_item(self):
        response = self.client.post(
            reverse("recipes:pantry"),
            {
                "ingredient": self.ingredient.pk,
                "quantity": "500",
                "unit": "g",
                "location": "pantry",
                "expiry_date": "",
            },
        )
        self.assertRedirects(response, reverse("recipes:pantry"))
        item = StockItem.objects.get(ingredient=self.ingredient)
        self.assertEqual(item.quantity, Decimal("500"))
        self.assertEqual(item.location, "pantry")

    def test_edit_stock_item(self):
        item = StockItem.objects.create(
            ingredient=self.ingredient, quantity=100, unit="g", location="fridge"
        )
        response = self.client.post(
            reverse("recipes:edit_stock_item", args=[item.pk]),
            {
                "ingredient": self.ingredient.pk,
                "quantity": "250",
                "unit": "g",
                "location": "freezer",
                "expiry_date": "",
            },
        )
        self.assertRedirects(response, reverse("recipes:pantry"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("250"))
        self.assertEqual(item.location, "freezer")

    def test_delete_stock_item(self):
        item = StockItem.objects.create(ingredient=self.ingredient, quantity=100, unit="g")
        response = self.client.post(reverse("recipes:delete_stock_item", args=[item.pk]))
        self.assertRedirects(response, reverse("recipes:pantry"))
        self.assertFalse(StockItem.objects.filter(pk=item.pk).exists())

    def test_is_expiring_soon_boundaries(self):
        no_expiry = StockItem.objects.create(ingredient=self.ingredient, quantity=1, unit="g")
        self.assertFalse(no_expiry.is_expiring_soon)
        self.assertFalse(no_expiry.is_expired)

        exactly_at_threshold = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() + timedelta(days=StockItem.EXPIRY_WARNING_DAYS),
        )
        self.assertTrue(exactly_at_threshold.is_expiring_soon)

        just_after_threshold = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() + timedelta(days=StockItem.EXPIRY_WARNING_DAYS + 1),
        )
        self.assertFalse(just_after_threshold.is_expiring_soon)

        expired = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() - timedelta(days=1),
        )
        self.assertTrue(expired.is_expired)
        self.assertTrue(expired.is_expiring_soon)

    def test_pantry_list_sorted_soonest_expiry_first_nulls_last(self):
        no_expiry = StockItem.objects.create(ingredient=self.ingredient, quantity=1, unit="g")
        soon = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() + timedelta(days=1),
        )
        later = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() + timedelta(days=10),
        )
        self.assertEqual(
            list(StockItem.objects.values_list("pk", flat=True)),
            [soon.pk, later.pk, no_expiry.pk],
        )

    def test_expiry_badge_shown_on_pantry_page(self):
        StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=1,
            unit="g",
            expiry_date=date.today() - timedelta(days=1),
        )
        response = self.client.get(reverse("recipes:pantry"))
        self.assertContains(response, "Périmé")


class StockIntegrationTests(RecipesTestCase):
    def test_generate_subtracts_available_stock(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )
        StockItem.objects.create(ingredient=self.ingredient, quantity=30, unit="g")

        self.client.post(reverse("recipes:generate_shopping_list", args=[self.year, self.week]))

        item = ShoppingListItem.objects.get(ingredient=self.ingredient)
        self.assertEqual(item.quantity, Decimal("70"))

    def test_generate_drops_line_when_stock_fully_covers_need(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=self.monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )
        StockItem.objects.create(ingredient=self.ingredient, quantity=150, unit="g")

        self.client.post(reverse("recipes:generate_shopping_list", args=[self.year, self.week]))

        self.assertFalse(ShoppingListItem.objects.filter(ingredient=self.ingredient).exists())

    def test_mark_cooked_deducts_soonest_expiring_lot_first(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=80, unit="g"
        )
        soon = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=50,
            unit="g",
            expiry_date=date.today() + timedelta(days=1),
        )
        later = StockItem.objects.create(
            ingredient=self.ingredient,
            quantity=100,
            unit="g",
            expiry_date=date.today() + timedelta(days=30),
        )

        self.client.post(reverse("recipes:mark_cooked", args=[recipe.pk]))

        self.assertFalse(StockItem.objects.filter(pk=soon.pk).exists())
        later.refresh_from_db()
        self.assertEqual(later.quantity, Decimal("70"))  # 80 needed - 50 (soon) = 30 taken from later

    def test_mark_cooked_reduces_lot_without_deleting_when_more_than_needed(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=20, unit="g"
        )
        lot = StockItem.objects.create(ingredient=self.ingredient, quantity=100, unit="g")

        self.client.post(reverse("recipes:mark_cooked", args=[recipe.pk]))

        lot.refresh_from_db()
        self.assertEqual(lot.quantity, Decimal("80"))

    def test_mark_cooked_best_effort_when_stock_insufficient(self):
        recipe = Recipe.objects.create(title="A", prep_time_min=10)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=500, unit="g"
        )
        StockItem.objects.create(ingredient=self.ingredient, quantity=50, unit="g")

        response = self.client.post(reverse("recipes:mark_cooked", args=[recipe.pk]))

        self.assertRedirects(response, reverse("recipes:detail", args=[recipe.pk]))
        self.assertFalse(StockItem.objects.filter(ingredient=self.ingredient).exists())
        recipe.refresh_from_db()
        self.assertEqual(recipe.last_cooked_on, date.today())
