# Obsidian Machine Knowledge Template

Un coffre Obsidian public et réutilisable pour documenter une machine, ses services, ses décisions et leurs preuves — sans exporter le contenu d'une machine existante.

## Inclus

- une structure gouvernée : vérité actuelle, décisions, travail, preuves et sources brutes ;
- un cockpit `Home.md`, un atlas Canvas et trois Bases natives ;
- une configuration visuelle sobre : AnuPpuccin, Notebook Navigator et Extended Graph ;
- des modèles de notes sans dépendance à Templater ;
- `SETUP_PROMPT.md`, prêt à donner à un agent sur une nouvelle machine ;
- un contrôle de confidentialité exécutable et en CI.

## Démarrage

```bash
git clone <URL_DU_REPO> machine-knowledge
cd machine-knowledge
python3 scripts/check_public.py
```

1. Ouvrir ce dossier comme coffre Obsidian.
2. Installer le thème et les plugins listés dans `plugins.lock.json` depuis les catalogues Obsidian.
3. Copier le contenu de `SETUP_PROMPT.md` dans votre agent et remplacer les variables entre chevrons.
4. Examiner le plan proposé avant d'autoriser l'ingestion.

`community-plugins.json` active les plugins mais ne contient pas leurs binaires. C'est volontaire : Obsidian les installe depuis leurs distributions officielles.

## Organisation

```text
Home.md                  cockpit
Atlas.canvas             carte visuelle dérivée
knowledge/
  index.md                règles et couches d'autorité
  truth/                  état actuel confirmé
  decisions/              choix et raisons
  work/                   hypothèses et analyses
  evidence/               observations vérifiables
  raw/                    captures non fiables
  assets/                 médias locaux
_dashboards/              vues Bases natives
_templates/               modèles de notes
```

Une information n'a qu'un propriétaire canonique. Les Bases, Canvas et graphes sont des vues : ils ne deviennent jamais une source de vérité.

## Confidentialité

Le dépôt est construit par liste blanche. Il ne contient ni état d'interface, historique récent, récupération de fichiers, session d'agent, configuration SSH, jeton, chemin utilisateur ni binaire tiers.

Avant chaque publication :

```bash
python3 scripts/check_public.py
# Optionnel si installé : gitleaks dir .
```

Voir `SECURITY.md` avant d'ajouter un nouveau fichier sous `.obsidian/`.
