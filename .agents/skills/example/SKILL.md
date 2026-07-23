---
name: workspace-census
description: Inventorie un nouveau projet et prépare son bundle OKF, son registre visuel et son état Extended Graph.
---

# Workspace census

1. Inspecter le projet en lecture seule.
2. Proposer `id`, `path`, `color` et `icon`.
3. Créer `docs/index.md` et uniquement les couches nécessaires.
4. Mettre à jour `docs/projects.md`, `docs/cross-project-map.md` et `workspace.projects.json`.
5. Exécuter `python3 scripts/sync_visuals.py` puis `--check`.
6. Valider avec `kb okf validate`.
