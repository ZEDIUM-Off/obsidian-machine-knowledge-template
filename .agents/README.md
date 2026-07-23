# `.agents` — operational workspace state

Ce dossier porte l'état transitoire utile aux agents. Il ne contient pas de vérité métier canonique.

```text
state/current-focus.md         tâche active, next steps, blocages
state/workspace-inventory.md   présence et état des projets
state/project-relations.md     relations découvertes à confirmer
state/migration-notes.md       chemins et migrations différées
ideas/                         une idée ou friction par fichier
skills/                        skills propres au workspace
```

Une information stabilisée quitte `.agents/` pour son propriétaire canonique sous `docs/` ou `<project>/docs/`.
