---
type: Guide
title: Extended Graph project states
status: active
authority: canonical
sensitivity: public
agent_access: write
tags:
  - review/human-required
timestamp: 2026-07-23
---

# Extended Graph project states

## Source unique

`workspace.projects.json` porte pour chaque projet :

- `id` stable en kebab-case ;
- `path` relatif au vault ;
- `color` hexadécimale unique ;
- `icon` Lucide.

Ne modifier directement ni les états Extended Graph ni les couleurs Notebook Navigator. Lancer `python3 scripts/sync_visuals.py`.

## États obligatoires

| État | Filtre |
|---|---|
| `Workspace Atlas` | tout le vault, groupes colorés par projet |
| `Current Truth` | `[authority:canonical] -[status:superseded]` |
| `Human Review` | `tag:#review/human-required` |
| `Agent Surface` | `.agents`, `.pi` et aliases globaux |
| `Project · <id>` | `path:"<project-path>/"` |

Chaque état projet utilise la couleur du registre et active liens entrants/sortants à profondeur 1. `.pi-subagents` reste exclu.

## Icônes

Extended Graph lit la propriété `icon` et hérite de l'icône parente. Notebook Navigator reçoit la même icône pour le dossier projet. La note projet sous `docs/projects.md` et le `docs/index.md` du projet conservent aussi `icon` et `color` en frontmatter.

## Contrôle

```bash
python3 scripts/sync_visuals.py --check
```

Le contrôle échoue si un projet n'a pas exactement un état, si une couleur/icône diverge ou si un état `.pi-subagents` apparaît.
