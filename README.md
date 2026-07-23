# Obsidian Machine Knowledge Workspace

Template d'un **workspace Obsidian unique** qui réunit documentation machine, projets, état agentique, workflows et recherche gouvernée.

Le dépôt fournit uniquement la structure, les normes OKF, la configuration visuelle et les outils reproductibles. Les connaissances d'une machine sont ingérées ensuite avec `SETUP_PROMPT.md`.

## Architecture

```text
AGENTS.md                         règles d'entrée pour les agents
Home.md                           cockpit Obsidian
docs/                             vérité globale et registres
  projects.md                     registre humain des projets
  cross-project-map.md            dépendances entre projets
  knowledge-system/               normes OKF et contrat agent
  agents/                         règles .agents, .pi et skills
  setup/                          connaissance machine
  bases/                          vues natives dérivées
.agents/                          état opérationnel transitoire
  state/                          focus, inventaire, relations, migrations
  ideas/                          backlog agent/harness
  skills/                         skills propres au workspace
.pi/graphs/                       workflows exécutables du workspace
example-project/                  exemple de dépôt projet à la racine
  docs/                           bundle OKF possédé par le projet
.obsidian/                        interface et plugins configurés
tools/kb/                         CLI de connaissance gouvernée
tools/bin/obsidian-relevant-tree  scanner des arbres visibles
workspace.projects.json           registre visuel unique
```

## Modèle de connaissance

Chaque bundle déclare ses couches dans `docs/index.md` ou `<project>/docs/index.md` :

```text
raw → evidence → work → accepted decision → truth
```

- `truth/` : ce qui s'applique maintenant ;
- `decisions/` : choix explicites et raisons ;
- `work/` : hypothèses, analyses et options ;
- `evidence/` : observations attribuables ;
- `raw/` : sources non interprétées.

Les Bases, Canvas et graphes sont des vues dérivées. Ils n'établissent jamais l'autorité d'une information.

## Système visuel

`workspace.projects.json` est l'unique registre pour `id`, `path`, `color` et `icon`.

```bash
python3 scripts/sync_visuals.py
python3 scripts/sync_visuals.py --check
```

La synchronisation produit :

- `Workspace Atlas` avec une couleur par projet ;
- `Current Truth` ;
- `Human Review` ;
- `Agent Surface` pour `.agents`, `.pi`, `.agents-global` et `.pi-global` ;
- exactement un état Extended Graph `Project · <id>` par projet ;
- les mêmes couleurs et icônes dans Notebook Navigator ;
- les groupes de couleur du graphe natif.

Ajouter un projet signifie donc : créer son bundle, l'enregistrer dans `docs/projects.md`, l'ajouter à `workspace.projects.json`, puis lancer `sync_visuals.py`.

## Agents, skills et workflows

- `AGENTS.md` reste court et référence les normes durables.
- `.agents/` porte uniquement l'état de travail transitoire.
- `.pi/graphs/` porte les workflows exécutables.
- un skill propre à un projet vit dans `<project>/.agents/skills/<name>/SKILL.md` ;
- un skill réutilisable vit dans `~/.agents/skills/` et peut être exposé par `.agents-global` ;
- `.pi-subagents/` reste un artefact d'exécution et n'entre jamais dans Obsidian ou Extended Graph.

Voir `docs/agents/state-and-skills.md`.

## CLI `kb`

Le CLI sous `tools/kb/` applique l'ordre d'autorité, les contrôles d'accès, les citations, les projections QMD et le protocole proposal/apply.

```bash
python3 -m pip install ./tools/kb
mkdir -p ~/.config/kb
cp config/kb/config.example.yml ~/.config/kb/config.yml
# adapter vault: dans le fichier
kb doctor
kb status
kb truth "architecture actuelle"
kb okf validate
```

Commandes principales : `query`, `truth`, `decisions`, `evidence`, `read`, `related`, `provenance`, `canvas`, `conflicts`, `review list`, `capture --dry-run`, `promote --dry-run`, `apply`.

## Installation

1. Cloner le dépôt à l'emplacement qui deviendra le workspace.
2. Suivre `SETUP_PROMPT.md` avec un agent local.
3. Installer le thème et les plugins de `plugins.lock.json` depuis Obsidian.
4. Installer `kb` et `obsidian-relevant-tree`.
5. Remplacer le projet d'exemple par les projets détectés.
6. Exécuter `python3 scripts/sync_visuals.py` puis ouvrir `Home.md`.
