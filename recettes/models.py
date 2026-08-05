"""Modèles du domaine recettes -- Phase 1.

Fidèle à docs/02-modele-donnees.md. Une simplification assumée : `RecetteTag` n'est pas modélisé
comme une classe séparée puisqu'il ne porte aucune donnée propre -- un ManyToManyField Django
standard représente exactement la même relation sans ajouter de code inutile.
"""

from django.db import models


class Ingredient(models.Model):
    class CategorieRayon(models.TextChoices):
        FRUITS_LEGUMES = "fruits_legumes", "Fruits & légumes"
        EPICERIE = "epicerie", "Épicerie"
        SURGELES = "surgeles", "Surgelés"
        PRODUITS_LAITIERS = "produits_laitiers", "Produits laitiers"
        VIANDE_POISSON = "viande_poisson", "Viande & poisson"
        BOISSONS = "boissons", "Boissons"
        AUTRE = "autre", "Autre"

    nom = models.CharField(max_length=100, unique=True)
    unite_par_defaut = models.CharField(max_length=20)
    categorie_rayon = models.CharField(
        max_length=20, choices=CategorieRayon.choices, default=CategorieRayon.AUTRE
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Tag(models.Model):
    nom = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Recette(models.Model):
    class ScoreNutritionnel(models.TextChoices):
        LEGER = "leger", "Léger"
        EQUILIBRE = "equilibre", "Équilibré"
        GOURMAND = "gourmand", "Gourmand"

    titre = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="recettes/", blank=True, null=True)
    temps_preparation_min = models.PositiveIntegerField()
    temps_cuisson_min = models.PositiveIntegerField(default=0, blank=True)
    portions_defaut = models.PositiveIntegerField(default=4)
    score_nutritionnel = models.CharField(
        max_length=20, choices=ScoreNutritionnel.choices, default=ScoreNutritionnel.EQUILIBRE
    )
    derniere_cuisson_le = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name="recettes", blank=True)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return self.titre


class Etape(models.Model):
    recette = models.ForeignKey(Recette, related_name="etapes", on_delete=models.CASCADE)
    ordre = models.PositiveIntegerField()
    description = models.TextField()

    class Meta:
        ordering = ["ordre"]

    def __str__(self):
        return f"{self.recette.titre} - étape {self.ordre}"


class RecetteIngredient(models.Model):
    recette = models.ForeignKey(
        Recette, related_name="recette_ingredients", on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantite = models.DecimalField(max_digits=6, decimal_places=2)
    unite = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.quantite} {self.unite} {self.ingredient.nom}"
