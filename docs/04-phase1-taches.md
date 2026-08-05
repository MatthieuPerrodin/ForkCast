# ForkCast — Phase 1 : découpage en tâches

> Dérivé de [01-cahier-des-charges.md](01-cahier-des-charges.md) (user stories Phase 1) et de
> [02-modele-donnees.md](02-modele-donnees.md). Stack : [03-stack-technique.md](03-stack-technique.md).

## Milestone 1.0 — Amorçage du projet ✅

- [x] T1 — Nouveau projet Django (`forkcast`) à la racine, remplace l'ancien prototype.
- [x] T2 — Config par variables d'environnement (`.env`) : `SECRET_KEY`, `DEBUG`, `DATABASE_URL`.
      Bascule automatique SQLite (local, zéro setup) / PostgreSQL (dès que `DATABASE_URL` pointe
      vers Supabase).
- [x] T3 — `.gitignore` + dépôt git initialisé.
- [x] T4 — Template de base (`base.html`) avec htmx + Alpine.js (CDN) + Pico.css (styling minimal
      sans étape de build), layout minimal.
- [x] T5 — Auth minimale : un seul compte, page de login simple (vues `LoginView`/`LogoutView`
      natives de Django, pas de signup, compte créé via `createsuperuser`).

## Milestone 1.1 — Modèle de données recettes ✅

- [x] T6 — Modèles `Ingredient`, `Tag`, `Recette`, `Etape`, `RecetteIngredient` (app `recettes`),
      fidèles à [02-modele-donnees.md](02-modele-donnees.md). `RecetteTag` implémenté comme un
      `ManyToManyField` Django standard plutôt qu'un modèle séparé (ne porte aucune donnée propre).
- [x] T7 — Migrations initiales, appliquées et vérifiées sur SQLite local.
- [x] T8 — Enregistrement dans l'admin Django (inlines pour ingrédients/étapes directement sur la
      fiche recette).

## Milestone 1.2 — CRUD Recettes (interface utilisateur)

- [x] T9 — Vue liste des recettes + recherche par nom + filtre par tag.
- [x] T10 — Vue détail d'une recette + ajustement dynamique des quantités selon le nombre de
      portions souhaité (recalcul côté client via Alpine.js, sans aller-retour serveur).
- [x] T11 — Formulaire de création de recette (titre, description, photo, temps, portions,
      tags) avec sous-formulaire dynamique pour les ingrédients (ajout/suppression de lignes en
      htmx, via `inlineformset_factory` + endpoints htmx dédiés).
- [x] T12 — Sous-formulaire dynamique pour les étapes (ajout/suppression, ordre).
- [x] T13 — Modification d'une recette existante (réutilise le même formulaire/vue que T11).
- [x] T14 — Suppression d'une recette (confirmation via `confirm()` JS avant le POST).
- [ ] T15 — Upload de photo — le champ existe déjà (`ImageField` sur `Recette`, stockage local via
      `MEDIA_ROOT`) ; bascule vers Supabase Storage documentée comme tâche séparée (Milestone 1.4)
      plutôt que bloquante ici.

## Milestone 1.3 — Fonctionnalité phare V1 (Sens A, cf. cahier des charges §5)

- [x] T16 — Champ `derniere_cuisson_le` + action "j'ai cuisiné ça" pour le mettre à jour depuis la
      fiche recette.
- [x] T17 — Vue "Surprends-moi" : filtre par temps de préparation et score nutritionnel, tri
      anti-répétition (`nulls_first` sur `derniere_cuisson_le`, tirage parmi les 5 candidats les
      moins récemment cuisinés).

## Milestone 1.4 — Finitions

- [ ] T18 — Bascule effective du stockage photo vers Supabase Storage.
- [ ] T19 — Déploiement initial sur Google Cloud Run (Dockerfile, variables d'env de prod).
- [ ] T20 — Revue rapide responsive (mobile/desktop) sur les pages liste/détail/formulaire.

## Notes

- Ce document est une checklist de travail, pas figée : cocher au fur et à mesure, ajouter/retirer
  des tâches si le besoin évolue en cours de route. Toute décision qui s'écarte de ce plan doit
  être tracée dans [00-journal-de-bord.md](00-journal-de-bord.md).
