from datetime import date, timedelta
from decimal import Decimal

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


class ShoppingListTests(RecipesTestCase):
    def setUp(self):
        super().setUp()
        self.year, self.week, _ = date.today().isocalendar()
        self.monday = date.fromisocalendar(self.year, self.week, 1)
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
        self.assertContains(response, "en rabais")

        year, week, _ = date.today().isocalendar()
        response = self.client.get(reverse("recipes:planning_week", args=[year, week]))
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
        year, week, _ = date.today().isocalendar()
        monday = date.fromisocalendar(year, week, 1)
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )
        StockItem.objects.create(ingredient=self.ingredient, quantity=30, unit="g")

        self.client.post(reverse("recipes:generate_shopping_list", args=[year, week]))

        item = ShoppingListItem.objects.get(ingredient=self.ingredient)
        self.assertEqual(item.quantity, Decimal("70"))

    def test_generate_drops_line_when_stock_fully_covers_need(self):
        year, week, _ = date.today().isocalendar()
        monday = date.fromisocalendar(year, week, 1)
        recipe = Recipe.objects.create(title="A", prep_time_min=10, default_servings=2)
        RecipeIngredient.objects.create(
            recipe=recipe, ingredient=self.ingredient, quantity=100, unit="g"
        )
        MealSlot.objects.create(
            date=monday, meal_time="lunch", recipe=recipe, planned_servings=2
        )
        StockItem.objects.create(ingredient=self.ingredient, quantity=150, unit="g")

        self.client.post(reverse("recipes:generate_shopping_list", args=[year, week]))

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
