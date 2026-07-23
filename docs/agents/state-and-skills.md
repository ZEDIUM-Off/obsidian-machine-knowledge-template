---
type: Governance
title: Agent state, workflows and skills
status: active
authority: canonical
sensitivity: public
agent_access: write
tags:
  - review/human-required
timestamp: 2026-07-23
---

# Agent state, workflows and skills

## `.agents/`

État opérationnel lisible : focus courant, inventaire, relations découvertes, migrations, handoffs et idées. Cet état peut devenir obsolète et ne remplace jamais une note canonique.

## `.pi/graphs/`

Workflows exécutables et états d'orchestration. Un graphe peut lire ou proposer de la connaissance, mais son checkpointer n'est pas une autorité sémantique.

## Skills locaux

Créer `<project>/.agents/skills/<name>/SKILL.md` seulement pour une procédure liée au projet. Le frontmatter minimal est :

```yaml
---
name: example-skill
description: Déclencheur précis et résultat attendu.
---
```

Les scripts et références relatifs restent dans le dossier du skill. Un skill ne doit pas dupliquer `AGENTS.md` ou une norme globale.

## Skills globaux

Les skills réutilisables vivent sous `~/.agents/skills/`. L'alias `.agents-global` permet leur inspection dans Obsidian sans les copier. Le lock d'installation est opérationnel ; il ne devient pas vérité métier.

## Admission

1. besoin observé ;
2. source et licence identifiées ;
3. contenu lu entièrement ;
4. outils et écritures compris ;
5. installation minimale ;
6. déclencheur documenté ;
7. suppression possible sans perte de connaissance.
