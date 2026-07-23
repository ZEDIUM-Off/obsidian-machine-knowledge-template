---
type: Governance
title: Knowledge system specification
status: accepted
authority: canonical
sensitivity: public
agent_access: write
okf_version: "0.1"
tags:
  - review/human-required
timestamp: 2026-07-23
---

# Knowledge system specification

| Concern | Specification |
|---|---|
| Vault et ownership | [[vault-architecture]] |
| OKF, couches et provenance | [[knowledge-model]] |
| Accès, retrieval et écritures agent | [[agent-contract]] |
| QMD et projections | [[qmd-retrieval]] |

## Invariants

- un vault unique contient plusieurs bundles gouvernés ;
- Markdown/YAML/Canvas/assets sont la vérité filesystem ;
- l'autorité vient des couches OKF, jamais du score de recherche ;
- `docs/` possède le global, chaque projet possède son interne ;
- `.agents/` et `.pi/` restent opérationnels ;
- Bases, Canvas et graphes restent dérivés ;
- les index QMD et propositions vivent hors du vault.
