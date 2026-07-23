# Workspace agent contract

## Avant tout travail

1. Lire `docs/index.md`, `docs/projects.md` et `docs/cross-project-map.md`.
2. Lire `docs/knowledge-system/index.md` et les modules liés à la tâche.
3. Lire `.agents/state/` pour le focus et les migrations en cours.
4. Consulter la vérité locale avec `kb truth` avant toute recherche externe.

## Structure

- `docs/` possède la vérité globale et les relations transverses.
- Chaque dépôt projet à la racine possède sa vérité dans `<project>/docs/`.
- `.agents/` contient l'état opérationnel transitoire, jamais la vérité canonique.
- `.pi/graphs/` contient les workflows exécutables du workspace.
- Canvas, Bases, Notebook Navigator et Extended Graph sont des vues dérivées.

## Ajouter ou retirer un projet

Mettre à jour ensemble :

1. `workspace.projects.json` (`id`, `path`, `color`, `icon`) ;
2. `docs/projects.md` et la note projet associée ;
3. `<project>/docs/index.md` et ses couches OKF ;
4. `docs/cross-project-map.md` si une dépendance existe ;
5. `python3 scripts/sync_visuals.py`.

Un projet déclaré doit produire exactement un état Extended Graph `Project · <id>` et conserver la même couleur/icône dans le registre, Notebook Navigator et le graphe.

## Écriture gouvernée

- Toute note créée ou modifiée par un agent reçoit `review/human-required`.
- Utiliser `kb capture --dry-run` ou `kb promote --dry-run`, puis attendre une instruction distincte avant `kb apply <proposal-id>`.
- Un agent ne peut ni accepter sa propre décision, ni supprimer l'état de review, ni résoudre silencieusement une contradiction.
- Une seule source canonique par fait ; décisions et preuves la référencent au lieu de la dupliquer.

## Skills

- Skill local : `<project>/.agents/skills/<name>/SKILL.md`, seulement si son comportement est propre au projet.
- Skill global : `~/.agents/skills/<name>/SKILL.md`, exposé dans le vault par `.agents-global` si nécessaire.
- Chaque `SKILL.md` déclare au minimum `name` et `description` en frontmatter.
- Les chemins relatifs d'un skill sont résolus depuis son propre dossier.
- Auditer un skill avant installation ; ne jamais copier automatiquement un catalogue entier.

## Visibilité Obsidian

Seuls `.agents`, `.pi`, `.agents-global` et `.pi-global` peuvent être admis parmi les dot-directories. `.pi-subagents`, `.git`, caches, dépendances, builds et modèles restent exclus.
