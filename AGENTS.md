# AGENTS.md — ForkCast

## État du projet

- Projet Django `forkcast` (app `recettes`) amorcé et fonctionnel : modèles, admin, auth
  (login/logout natifs Django), vues liste/détail de recettes. Voir Milestones 1.0/1.1 cochés dans
  [docs/04-phase1-taches.md](docs/04-phase1-taches.md) pour l'état exact d'avancement de la
  Phase 1 — **toujours vérifier ce fichier avant de supposer qu'une fonctionnalité existe ou non.**
- `legacy/` contient l'**ancien prototype Django abandonné** (`core/`, `myrecipes/`, auth codée à
  la main, `core/models.py` vide) — conservé pour référence mais ne sert à rien pour la suite. Ne
  pas s'en servir comme référence d'architecture ou de conventions.
- La source de vérité sur le besoin, les données et la stack est dans `docs/` :
  - [docs/00-journal-de-bord.md](docs/00-journal-de-bord.md) — journal chronologique des décisions
    prises, leur raisonnement, et les leçons apprises. Sert de cas d'étude "projet mené de bout en
    bout" pour l'utilisateur. **Volontairement exclu du dépôt git** (listé dans `.gitignore`,
    considéré personnel par l'utilisateur) — le fichier existe et doit continuer à être tenu à
    jour localement, il ne doit simplement jamais être ajouté/commité/poussé.
  - [docs/01-cahier-des-charges.md](docs/01-cahier-des-charges.md) — vision, utilisateurs, feuille
    de route par phases, user stories, hors périmètre.
  - [docs/02-modele-donnees.md](docs/02-modele-donnees.md) — entités, relations, points ouverts.
  - [docs/03-stack-technique.md](docs/03-stack-technique.md) — stack validée : Python/Django
    (monolithe rendu serveur) + htmx/Alpine.js + PostgreSQL/Stockage via Supabase + hébergement
    Google Cloud Run.
  - [docs/04-phase1-taches.md](docs/04-phase1-taches.md) — checklist de tâches pour la Phase 1,
    à cocher/mettre à jour au fil de l'avancement réel (source de vérité sur ce qui est fait).
- **Lire ces documents avant de proposer du code, une architecture ou un modèle de données.**
- **Après toute décision structurante** (choix de stack, changement d'architecture, ajout/retrait
  de périmètre, leçon tirée d'une erreur) : ajouter une entrée à
  `docs/00-journal-de-bord.md` (date, contexte/décision, pourquoi, leçon si pertinente) avant de
  passer à la suite. Ne pas attendre la fin du projet pour documenter — c'est tout l'intérêt du
  journal.

## Comment travailler sur ce repo

- **Workflow git obligatoire pour toute étape importante** (une feature, un milestone du plan
  Phase X, un changement structurant) :
  1. Créer une branche dédiée depuis `master` (ex. `feature/formulaire-recette`,
     `feature/suggestion-surprends-moi`) — jamais commiter directement sur `master`.
  2. Développer, puis **tester réellement** avant d'ouvrir la PR (vérifier le chemin critique
     concerné — cf. règle de vérification ci-dessous — pas seulement `manage.py check`).
  3. Ouvrir une Pull Request sur GitHub (`gh pr create`) décrivant ce qui change et pourquoi.
  4. Merger la PR (`gh pr merge`) une fois relue/validée, puis supprimer la branche.
  - Pour un correctif trivial (typo, doc) isolé, ce cycle complet n'est pas nécessaire — mais dans
    le doute, l'appliquer plutôt que de pousser directement sur `master`.
- La stack (§ci-dessus) est validée — s'y tenir. Si un changement d'architecture ou d'outil
  semble nécessaire en cours de route, en discuter avec l'utilisateur avant d'implémenter, et
  documenter la décision dans `docs/03-stack-technique.md` + une entrée de journal.
- Toute nouvelle fonctionnalité doit se rattacher à une phase existante (1 à 5) du cahier des
  charges. Si elle n'y correspond pas, l'ajouter d'abord à la documentation (backlog ou nouvelle
  user story) avant d'écrire du code.
- Le projet vise un usage réel par un foyer avec **un seul compte partagé** (pas de multi-tenant,
  pas de permissions différenciées entre membres) — éviter de sur-ingénierer le scoping
  utilisateur ou les rôles/permissions.
- La fonctionnalité centrale du produit est la boucle repas ↔ courses bidirectionnelle (voir
  cahier des charges section 5) — en cas de doute sur la priorité d'une fonctionnalité, celle-ci
  passe avant le reste.
- Commandes utiles (venv dans `.venv/`) :
  - Lancer le serveur : `.venv/Scripts/python.exe manage.py runserver`
  - Migrations : `.venv/Scripts/python.exe manage.py makemigrations` puis `migrate`
  - Compte de dev local (SQLite, non commité) : `famille` / `forkcast-dev`
  - Pas de suite de tests automatisés pour l'instant (`recettes/tests.py` est vide) — à mettre en
    place au fil de l'implémentation des vues/formulaires restants.
- Après toute modification de vue/template touchant à l'authentification ou au CRUD recettes,
  vérifier le chemin critique réellement (login par POST + rendu de la page, pas seulement
  l'absence d'erreur au démarrage du serveur) avant de considérer la tâche terminée.

## Historique

- 2026-08-05 : reprise du projet depuis zéro côté besoin/produit ; cadrage, modèle de données et
  stack technique validés le même jour (voir `docs/00-journal-de-bord.md`) ; amorçage du projet
  Django `forkcast` avec les Milestones 1.0 et 1.1 de la Phase 1 complétés et vérifiés
  end-to-end. L'ancien prototype est archivé dans `legacy/`.
