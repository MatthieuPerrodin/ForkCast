# ForkCast — Cahier des charges

> Statut : brouillon de travail — à valider/amender avant de passer au choix de la stack technique.

## 1. Vision du projet

ForkCast est une application qui simplifie le quotidien alimentaire d'un foyer : **savoir quoi
manger et faire les courses sans y passer du temps ni se prendre la tête**. Elle centralise les
recettes, planifie les repas, génère la liste de courses, et suit le stock à la maison.

**Fonctionnalité phare** : une boucle repas ↔ courses **bidirectionnelle**, dans les deux sens
possibles, priorisée par **qualité nutritionnelle** et **rapidité de préparation** :
- *"J'ai ça à la maison, qu'est-ce que je cuisine ?"* (à partir du garde-manger)
- *"Qu'est-ce que je devrais acheter et cuisiner cette semaine ?"* (en tenant compte, idéalement,
  des rabais/promotions en magasin)

C'est le fil rouge qui relie les recettes, le garde-manger, le planning et la liste de courses
entre eux ; ce n'est pas une fonctionnalité secondaire ajoutée à la fin (détails §5).

## 2. Contexte & Motivation

- Projet personnel, à la fois **outil pratique** (usage réel au quotidien) et **projet
  d'apprentissage** (occasion d'explorer proprement l'architecture, les choix techniques, les
  bonnes pratiques).
- Reprise complète du projet précédent : l'ancienne base (Django, auth basique, aucun modèle
  métier) est mise de côté. On reconstruit en partant des besoins.

## 3. Utilisateurs cibles

- Un seul foyer/famille.
- **Un seul compte partagé** — pas de distinction entre membres du foyer, pas de permissions
  différenciées. Tout le monde voit et modifie les mêmes données (recettes, planning, stock).
- Usage prévu sur ordinateur (saisie de recettes, planification) et sur mobile (consultation en
  cuisine, liste de courses au supermarché) → l'interface doit être utilisable confortablement sur
  les deux.

## 4. Périmètre fonctionnel — feuille de route par phases

L'application est découpée en phases livrables indépendamment, pour avoir un outil utilisable dès
la Phase 1 plutôt que d'attendre un "grand soir".

### Phase 1 — MVP : Carnet de recettes
Gérer et consulter ses recettes. C'est la fondation dont dépendent toutes les phases suivantes.

### Phase 2 — Planning des repas
Organiser un calendrier de repas (semaine) en assignant des recettes existantes à des
jours/créneaux (midi/soir).

### Phase 3 — Liste de courses
Générer automatiquement une liste de courses agrégée à partir du planning de la semaine (ou d'une
sélection de recettes), en cumulant les ingrédients nécessaires.

### Phase 4 — Garde-manger
Suivre le stock à la maison : ingrédients présents, **quantités**, **dates de péremption**
(placards, frigo, congélateur). La liste de courses de la Phase 3 doit pouvoir soustraire ce qui
est déjà en stock.

### Phase 5 — Exploration IA / données externes (backlog, non prioritaire)
Pistes pour réduire la friction de saisie et enrichir la boucle repas ↔ courses, toutes dépendantes
d'une source de données externe ou d'un traitement IA — donc plus incertaines et à n'aborder
qu'une fois les phases 1-4 stables et le besoin éprouvé à l'usage :
- Reconnaissance de produits par photo pour le garde-manger.
- Scan/OCR d'un ticket de caisse pour réapprovisionner automatiquement le stock après les courses.
- Récupération automatique des rabais/circulaires des enseignes (scraping ou API type
  Flipp/Reebee) pour suggérer proactivement quoi acheter — voir Sens B §5.

## 5. Fonctionnalité phare : boucle repas ↔ courses bidirectionnelle

Le besoin réel n'est pas "avoir un carnet de recettes" mais "savoir quoi manger et quoi acheter,
sans se prendre la tête" — et ça marche dans les deux sens.

### Sens A — "J'ai ça à la maison, qu'est-ce que je cuisine ?"
- **V1 (dès la Phase 1, sans attendre le garde-manger)** : à partir du carnet de recettes,
  proposer une recette (ou une short-list) filtrée/triée par temps de préparation et par tag
  nutritionnel (ex. "rapide", "équilibré"), avec un bouton type "Surprends-moi" qui respecte les
  filtres actifs. Évite la répétition en dépriorisant les recettes cuisinées récemment.
- **V2 (une fois le garde-manger en place, Phase 4)** : croiser les recettes avec le stock réel
  disponible pour prioriser celles où la majorité des ingrédients sont déjà à la maison, toujours
  pondéré par rapidité et qualité nutritionnelle. C'est la version "aboutie" de ce sens.

### Sens B — "Qu'est-ce que je devrais acheter et cuisiner cette semaine ?"
- **V1 (manuel, dès la Phase 3 Liste de courses)** : l'utilisateur indique à la main quels
  ingrédients sont en rabais cette semaine (et éventuellement le prix promo, en regardant la
  circulaire lui-même). L'appli met en avant les recettes qui utilisent ces ingrédients au moment
  de planifier/générer la liste de courses.
- **V2 (backlog, Phase 5, ambitieux)** : récupération automatique des circulaires/rabais des
  enseignes pour suggérer proactivement quoi acheter et cuisiner, sans saisie manuelle. Dépend
  d'une source de données fiable côté épiceries (scraping ou API) — complexité comparable à l'OCR
  de ticket de caisse, à évaluer en temps voulu plutôt qu'assumée dès le départ.

### Idées inspirées d'applications existantes (backlog, à trier)

À évaluer au fil de l'eau, une fois les phases 1-4 stables — proposées pour inspiration, aucune
n'est engagée pour l'instant :

- **Liste de courses triée par rayon de magasin** (fruits/légumes, épicerie, surgelés...) pour
  aller plus vite en courses — peu coûteux à préparer dès maintenant en ajoutant un champ
  "catégorie" sur le référentiel d'ingrédients (cf. modèle de données).
- **Import de recette depuis une URL** (le site fait souvent l'objet d'un simple copier-coller) —
  évite la ressaisie manuelle, gain de temps important pour remplir le carnet au départ.
- **Gestion des restes** : "il me reste X grammes de Y, qu'est-ce que je peux en faire ?" — variante
  ciblée de la suggestion de repas.
- **Filtres régime/allergies** (végétarien, sans gluten...) appliqués aux suggestions et à la
  génération de liste de courses.
- **Rotation/anti-répétition** : éviter de proposer 3 fois la même recette dans la semaine.
- **Score ou label nutritionnel simple** par recette (ex. inspiré du Nutri-Score) plutôt qu'un
  calcul calorique complet — reste simple à saisir/maintenir.
- **Notifications péremption** ("ça périme dans 2 jours, cuisine-le") — lié à la Phase 4.
- **Estimation de coût** des courses — utile mais pas prioritaire par rapport au nutritionnel/rapide.

## 6. Besoins fonctionnels détaillés (user stories)

### Phase 1 — Recettes
- En tant qu'utilisateur, je peux créer une recette avec : titre, photo (optionnelle), liste
  d'ingrédients (nom, quantité, unité), étapes de préparation, temps de préparation/cuisson,
  nombre de portions.
- En tant qu'utilisateur, je peux modifier ou supprimer une recette existante.
- En tant qu'utilisateur, je peux consulter la liste de mes recettes et ouvrir le détail de l'une
  d'elles.
- En tant qu'utilisateur, je peux rechercher/filtrer mes recettes (par nom, par tag/catégorie —
  ex. "végétarien", "rapide", "dessert").
- En tant qu'utilisateur, je peux ajuster les quantités affichées d'une recette selon le nombre de
  portions souhaité.

### Phase 2 — Planning
- En tant qu'utilisateur, je peux voir un calendrier hebdomadaire de repas (midi/soir par jour).
- En tant qu'utilisateur, je peux assigner une recette existante à un créneau du planning.
- En tant qu'utilisateur, je peux retirer ou remplacer une recette d'un créneau.
- En tant qu'utilisateur, je peux naviguer entre les semaines (précédente/suivante).

### Phase 3 — Liste de courses
- En tant qu'utilisateur, je peux générer une liste de courses à partir du planning de la semaine
  en cours.
- Les ingrédients communs à plusieurs recettes sont agrégés (quantités additionnées, même unité).
- En tant qu'utilisateur, je peux cocher les articles au fur et à mesure des achats.
- En tant qu'utilisateur, je peux ajouter manuellement des articles hors recette à la liste.
- En tant qu'utilisateur, je peux marquer un ingrédient comme "en rabais cette semaine" (prix
  optionnel), et voir les recettes qui l'utilisent mises en avant lors de la planification
  (Sens B §5, V1 manuel).

### Phase 4 — Garde-manger
- En tant qu'utilisateur, je peux ajouter/modifier un article en stock : nom, quantité, unité,
  emplacement (placard/frigo/congélateur), date de péremption.
- En tant qu'utilisateur, je suis alerté des articles proches de la péremption.
- La liste de courses (Phase 3) exclut ou réduit les quantités déjà disponibles en stock.
- Quand une recette du planning est "cuisinée", les quantités utilisées peuvent être déduites du
  stock (à affiner : automatique vs confirmation manuelle).

## 7. Besoins non fonctionnels

- **Responsive** : utilisable confortablement sur mobile (courses, consultation) et desktop
  (saisie de recettes).
- **Simplicité d'usage** avant tout — c'est un outil du quotidien, pas un outil pro : peu de
  friction pour ajouter une recette ou cocher une course.
- **Sécurité** : proportionnée à l'usage (compte unique partagé, pas de données sensibles de tiers)
  — pas besoin d'une architecture multi-tenant robuste pour l'instant, mais pas de secrets en dur
  dans le code.
- **Hébergement** : à définir (local/auto-hébergé vs cloud) — sujet de la discussion "stack
  technique" à venir.
- **Évolutivité raisonnable** : le modèle de données doit pouvoir absorber la Phase 4 (stock avec
  quantités/péremption) et laisser la porte ouverte à la Phase 5 (IA) sans tout réécrire — sans
  pour autant sur-ingénierer les phases 1-3.

## 8. Hors périmètre (pour l'instant)

- Multi-foyers / multi-tenants (l'appli sert un seul foyer).
- Gestion fine de permissions entre membres d'un même foyer.
- Application mobile native (on vise du web responsive dans un premier temps).
- Fonctionnalités IA (Phase 5) : non spécifiées, non développées avant que les phases 1-4 soient
  stables et utilisées réellement.

## 9. Prochaines étapes

1. Valider/amender ce document avec l'utilisateur.
2. Détailler le modèle de données (entités : Recette, Ingrédient, Étape, Planning, ArticleCourse,
   ArticleStock...) — un ADR ou schéma dédié.
3. Choisir la stack technique (sujet séparé, après validation du besoin).
4. Découper la Phase 1 en tickets/tâches concrets.
