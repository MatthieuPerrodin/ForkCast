# ForkCast — Stack technique

> Statut : validé avec l'utilisateur le 2026-08-05. Dérivé du besoin
> ([01-cahier-des-charges.md](01-cahier-des-charges.md)) et du modèle de données
> ([02-modele-donnees.md](02-modele-donnees.md)).

## 1. Vue d'ensemble

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage | Python | Familiarité acquise sur le prototype précédent ; écosystème solide pour d'éventuelles features IA (Phase 5). |
| Framework web | Django (monolithe rendu serveur) | Batteries incluses (ORM, admin, auth), un seul projet à maintenir en solo, colle naturellement au modèle relationnel défini. |
| Interactivité front | Django templates + htmx + Alpine.js | Effet "app réactive" (cases à cocher, calendrier de planning) sans construire une SPA séparée ni une API dédiée. |
| Base de données | PostgreSQL via **Supabase** | Managé, tier gratuit généreux, l'utilisateur le connaît déjà (projet finances perso) — inclut aussi le stockage de fichiers, réutilisé pour les photos de recettes. |
| Stockage fichiers | Supabase Storage | Évite d'ajouter un service de plus juste pour les photos de recettes ; déjà inclus avec Supabase. |
| Hébergement app | **Google Cloud Run** | Conteneurisé (Docker), scale-à-zéro (coût nul à faible usage), déjà pratiqué par l'utilisateur sur un projet précédent. |

## 2. Ce qui reste ouvert

- **Hors-ligne pour la liste de courses (Phase 3)** : non tranché. L'architecture retenue ne ferme
  pas cette porte — on pourra ajouter un *manifest.json* + un *service worker* ciblés sur la page
  liste de courses le moment venu, sans réarchitecturer le reste.
- **Conversion d'unités** (voir modèle de données §5) : reste un problème d'implémentation à
  traiter au moment de coder les recettes/courses, pas un enjeu de stack.

## 3. Alternative envisagée et écartée

**FastAPI + frontend séparé (React/Vue)** — plus "moderne" sur le papier, mais implique deux
codebases à maintenir pour un développeur solo, sans bénéfice réel pour ce projet (pas de besoin
de temps réel ni d'app mobile native qui justifierait cette complexité). Écarté au profit d'un
monolithe Django.

## 4. Composants techniques concrets (à mettre en place à l'amorçage du projet)

- Projet Django (nouveau, remplace `myrecipes`/`core` existants).
- `Dockerfile` pour le déploiement sur Cloud Run.
- Connexion à la base Postgres Supabase via variables d'environnement (pas de secrets en dur, cf.
  besoins non fonctionnels du cahier des charges §7).
- `django-htmx` + Alpine.js embarqué en CDN ou vendored, pas de build JS complexe (pas de
  webpack/vite nécessaires pour démarrer).

## 5. Prochaine étape

Découper la Phase 1 (carnet de recettes) en tâches concrètes, puis amorcer le projet Django avec
cette stack.
