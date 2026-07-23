---
type: Governance
title: Knowledge layers
status: active
authority: canonical
sensitivity: public
agent_access: write
okf_version: "0.1"
knowledge_layers:
  canonical:
    - truth/
  decisions:
    - decisions/
  working:
    - work/
  evidence:
    - evidence/
  raw:
    - raw/
tags:
  - review/human-required
timestamp: 2026-07-23
---

# Knowledge layers

| Dossier | Contenu | Autorité par défaut |
|---|---|---|
| `truth/` | état actuel confirmé | canonique |
| `decisions/` | choix, alternatives et raisons | travail jusqu'à acceptation humaine |
| `work/` | analyses, hypothèses et questions | travail |
| `evidence/` | observations attribuables | preuve |
| `raw/` | captures nettoyées mais non interprétées | brut |

## Chaîne de promotion

```text
raw → evidence → work → accepted decision → truth
```

Une décision explique pourquoi la vérité change. La note canonique indique ce qui s'applique maintenant.
