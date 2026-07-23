# Prompt — installer et ingérer un workspace machine

Copier le bloc suivant dans un agent local après avoir cloné ce dépôt.

---

Tu transformes ce template en workspace Obsidian canonique pour une nouvelle machine.

## Variables

- Racine du workspace/vault : `<VAULT_PATH>`
- Périmètre machine : `<SETUP_SCOPE>`
- OS principal : `<OS_OR_DISTRO>`
- Accès Remote SSH : `<enabled|disabled>`
- Racine globale des skills : `<GLOBAL_AGENTS_PATH, default ~/.agents>`
- Racine globale Pi : `<GLOBAL_PI_PATH, default ~/.pi>`

## Contrat

1. Lis complètement `AGENTS.md`, `docs/index.md`, `docs/knowledge-system/index.md`, `docs/agents/state-and-skills.md` et `docs/agents/extended-graph.md`.
2. Inspecte d'abord en lecture seule et présente le plan exact avant mutation.
3. N'invente ni projet, ni dépendance, ni décision acceptée.
4. Les secrets et credentials restent dans leurs stores opérationnels, jamais dans la connaissance.
5. Une note créée ou modifiée par agent reçoit `review/human-required`.
6. Canvas, Bases et graphes restent dérivés ; la vérité vit en Markdown/YAML.

## 1. Préflight

- Vérifie que `<VAULT_PATH>` est la racine du clone.
- Exécute :

```bash
python3 -m unittest scripts/test_sync_visuals.py
python3 -m unittest tools/kb/test_kb.py
```

- Inventorie les dossiers de premier niveau sans parcourir dépendances, caches, builds, modèles ou datasets.
- Lis `workspace.projects.json`, `docs/projects.md`, `docs/cross-project-map.md` et `.agents/state/`.
- Présente les projets détectés, les bundles existants et les fichiers à créer/modifier. Attends mon accord.

## 2. Installer les outils après accord

### `kb`

```bash
python3 -m pip install <VAULT_PATH>/tools/kb
mkdir -p ~/.config/kb
cp <VAULT_PATH>/config/kb/config.example.yml ~/.config/kb/config.yml
```

Remplace `vault:` par le chemin absolu `<VAULT_PATH>`. Garde les propositions sous `~/.local/state/kb/` et les projections sous `~/.cache/kb/`.

### Scanner Obsidian distant

```bash
install -Dm755 <VAULT_PATH>/tools/bin/obsidian-relevant-tree ~/.local/bin/obsidian-relevant-tree
cp <VAULT_PATH>/config/kb/obsidian-tree-ignore.example.txt ~/.config/kb/obsidian-tree-ignore.txt
```

Si les chemins diffèrent des valeurs par défaut, configure `KB_VAULT=<VAULT_PATH>`, `GLOBAL_AGENTS_PATH=<GLOBAL_AGENTS_PATH>` et `GLOBAL_PI_PATH=<GLOBAL_PI_PATH>` dans l'environnement utilisé par le scanner.

### Aliases agentiques

Créer seulement si les cibles existent :

```bash
ln -s <GLOBAL_AGENTS_PATH> <VAULT_PATH>/.agents-global
ln -s <GLOBAL_PI_PATH> <VAULT_PATH>/.pi-global
```

Ne crée jamais d'alias vers `.pi-subagents`.

## 3. Configurer Obsidian

- Ouvre `<VAULT_PATH>` comme vault unique.
- Installe le thème et les plugins épinglés dans `plugins.lock.json` depuis leurs distributions officielles.
- Le plugin custom `remote-relevant-tree` est déjà fourni sous `.obsidian/plugins/` avec sa licence et son self-test.
- Si Remote SSH est activé, vérifie que `remote-ssh` 1.1.7 et `~/.local/bin/obsidian-relevant-tree` fonctionnent ensemble.
- Configure Homepage sur `Home.md`.
- Vérifie AnuPpuccin + Style Settings, Notebook Navigator, Extended Graph, Canvas et Bases.

## 4. Ingérer la structure machine

Dans `docs/setup/`, proposer uniquement les types d'entités réellement utiles :

- Device : rôle, plateforme, matériel utile, état observé ;
- Application : version, rôle, méthode d'installation, vérification ;
- Access : relation logique entre appareils/services ;
- Procedure : démarrage, arrêt, diagnostic, sauvegarde, restauration.

Créer une Base native pour un type uniquement lorsqu'il devient un registre contrôlé. Séparer état observé et état désiré.

Classer la connaissance globale :

- état actuel confirmé → `docs/truth/` ;
- décision explicite → `docs/decisions/` ;
- analyse ou hypothèse → `docs/work/` ;
- observation attribuable → `docs/evidence/` ;
- source non interprétée → `docs/raw/`.

## 5. Ingérer chaque projet

Supprime le projet d'exemple une fois au moins un vrai projet identifié.

Pour chaque dépôt réel à la racine :

1. choisir un `id` kebab-case stable ;
2. choisir une couleur hex unique et une icône Lucide ;
3. créer ou vérifier `<project>/docs/index.md` ;
4. mapper uniquement les couches OKF réellement utilisées ;
5. créer `docs/projects/<id>.md` avec `project_id`, `project_path`, `icon` et `color`, puis le lier depuis `docs/projects.md` ;
6. ajouter les mêmes `{id, path, color, icon}` à `workspace.projects.json` ;
7. ajouter les dépendances vérifiées à `docs/cross-project-map.md` ;
8. mettre à jour `.agents/state/workspace-inventory.md` et `project-relations.md`.

Un projet possède son implémentation et son architecture interne. `docs/` global possède seulement son registre et ses relations transverses.

## 6. Générer l'organisation visuelle

Ne saisis pas les couleurs et états à trois endroits. Le registre unique est `workspace.projects.json`.

```bash
cd <VAULT_PATH>
python3 scripts/sync_visuals.py
python3 scripts/sync_visuals.py --check
```

Vérifie dans Extended Graph :

- `Workspace Atlas` ;
- `Current Truth` ;
- `Human Review` ;
- `Agent Surface` ;
- exactement un `Project · <id>` par projet ;
- aucune vue `.pi-subagents`.

Pour chaque projet, vérifie que :

- le filtre est `path:"<project-path>/"` ;
- le groupe Extended Graph utilise sa couleur ;
- Notebook Navigator utilise la même couleur et la même icône ;
- `docs/index.md` du projet expose `icon` et `color` ;
- les liens entrants/sortants sont visibles à profondeur 1.

## 7. Skills, état et workflows

- Skill propre à un projet → `<project>/.agents/skills/<name>/SKILL.md`.
- Skill réutilisable → `<GLOBAL_AGENTS_PATH>/skills/<name>/SKILL.md`.
- Ne duplique pas une norme de `AGENTS.md` dans un skill.
- Chaque skill a un déclencheur précis, des chemins relatifs à son dossier et une procédure de vérification.
- `.agents/state/` reflète le focus courant ; une information stabilisée est promue vers son bundle canonique.
- `.pi/graphs/` reçoit seulement les workflows réellement utilisés.

## 8. Retrieval et écritures gouvernées

```bash
kb doctor
kb status
kb okf validate
kb truth "current architecture"
kb conflicts
kb review list
```

Commencer avec la recherche lexicale. Ajouter QMD BM25 via les collections `knowledge-agent` et `knowledge-full` uniquement si nécessaire.

Pour écrire :

```bash
kb capture --dry-run --path <target.md> --content-file <candidate.md>
kb promote --dry-run --path <existing.md> --content-file <candidate.md>
```

Présente l'identifiant et le diff. N'exécute `kb apply <proposal-id>` qu'après une instruction distincte.

## 9. Acceptation

Rapporte :

- projets et bundles enregistrés ;
- états Extended Graph générés ;
- palette et icônes ;
- skills locaux/globaux admis ;
- état de `kb doctor`, `kb okf validate` et des tests ;
- liens Canvas manquants, conflits et notes en review ;
- fichiers modifiés et rollback.

Le setup est terminé quand chaque projet a un propriétaire canonique, un bundle, une couleur, une icône et exactement un état Extended Graph.

---
