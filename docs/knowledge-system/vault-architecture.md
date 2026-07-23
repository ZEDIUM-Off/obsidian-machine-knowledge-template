---
type: Governance
title: Vault architecture
status: accepted
authority: canonical
sensitivity: public
agent_access: write
okf_version: "0.1"
tags:
  - review/human-required
timestamp: 2026-07-23
---

# Vault architecture

## Boundary

Le workspace racine est l'unique vault Obsidian et l'unique filesystem canonique. Les dépôts projets restent des dossiers ordinaires à la racine ; leurs bundles `docs/` ne sont pas des vaults séparés.

## Ownership

| Connaissance | Propriétaire canonique |
|---|---|
| Politique globale et setup | `docs/` |
| Implémentation et architecture projet | `<project>/docs/` |
| Relation entre projets | `docs/cross-project-map.md` |
| État de travail agent | `.agents/`, non canonique |
| Workflow | `.pi/graphs/`, exécutable et non canonique |
| Base, Canvas ou graphe | vue dérivée |

## Filesystem

Formats canoniques : Markdown, YAML frontmatter, JSON Canvas et assets locaux. QMD, embeddings, caches, propositions et logs vivent hors du vault.

## Dot-directories visibles

Le scanner peut exposer uniquement `.agents`, `.pi`, `.agents-global` et `.pi-global`. Les symlinks globaux restent confinés à `~/.agents` et `~/.pi`. `.pi-subagents` n'est jamais une surface Obsidian.

## Heavy trees

Exclure `.git`, dépendances, environnements virtuels, caches, builds, coverage, modèles, datasets binaires et bases applicatives. Une documentation enregistrée sous un projet lourd reste admissible explicitement.
