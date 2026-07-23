---
type: Governance
title: QMD retrieval specification
description: Normative QMD collections, projections, query construction, ranking and fallback behavior.
tags:
  - vault/governance
  - retrieval/qmd
  - review/human-required
timestamp: 2026-07-18T00:00:00Z
status: accepted
spec_version: "0.1"
okf_version: "0.1"
agent_access: write
sensitivity: public
canonical: true
---

# QMD retrieval specification

## Role

QMD supplies semantic and lexical retrieval over canonical vault files. It is not a source of truth, policy engine or metadata authority.

QMD indexes are disposable and fully reconstructible.

## Runtime

QMD runs on the configured canonical vault host against `<vault-root>` or a projection built from it.

Client devices MUST NOT run authoritative QMD indexes over Remote SSH shadow-vault caches.

Expected capabilities:

- BM25/FTS for exact terminology;
- vector search for paraphrases;
- hybrid retrieval;
- reranking when models and resources are available;
- document retrieval with stable source mapping.

## Collections

The logical full collection is:

```text
knowledge-full
```

It includes eligible Markdown from registered bundles and explicitly selected project documentation.

When strong confidentiality is required, build a separate agent collection:

```text
knowledge-agent
```

The agent collection is a regenerated projection that excludes denied content before QMD reads it.

A post-query filter over a full index is not sufficient as a hard confidentiality boundary.

## Exclusions

Default excluded patterns include:

```text
**/.git/**
**/node_modules/**
**/vendor/**
**/.venv/**
**/venv/**
**/.cache/**
**/dist/**
**/build/**
**/coverage/**
**/target/**
**/.next/**
**/.nuxt/**
**/storybook-static/**
**/models/**
**/postgres/**
```

Large datasets and media are excluded unless a registered bundle explicitly includes supporting Markdown metadata.

QMD does not reliably follow symlinked directories. Collections MUST point at real directories or materialized projections.

## Frontmatter

Structured policy and authority MUST NOT depend on QMD ranking.

The current QMD ingestion behavior is assumed to include raw frontmatter until a black-box test proves otherwise.

Preferred target:

- Obsidian/direct parser reads YAML;
- QMD indexes Markdown bodies;
- original files remain unchanged.

If QMD lacks a supported transform hook, use a temporary projection outside the vault.

## Projection contract

Recommended location:

```text
~/.cache/kb/projections/<generation>/
```

A projection MUST:

- materialize files rather than symlink directories;
- preserve source-relative paths;
- remove YAML only from the indexed text;
- preserve the Markdown body byte-for-byte where possible;
- record source path, source hash and body start line;
- exclude denied content for agent-safe collections;
- be built into a new generation and atomically activated;
- remain deletable without data loss.

Example mapping record:

```json
{
  "projected": "example-project/docs/truth/architecture.md",
  "source": "<vault-root>/example-project/docs/truth/architecture.md",
  "source_sha256": "...",
  "body_start_line": 23,
  "authority": "canonical"
}
```

Mapping metadata is derived state, not a second source of truth.

## Query construction

The `obsidian-knowledge` skill constructs structured QMD queries itself.

It MUST NOT blindly pass the original question to an automatic query expander.

Available fields:

```text
intent:
lex:
vec:
hyde:
```

Guidance:

- `intent` disambiguates user purpose and scope;
- `lex` contains exact names, phrases, acronyms and exclusions;
- `vec` contains semantic paraphrases;
- `hyde` is reserved for queries where a hypothetical answer passage improves recall.

Example:

```text
intent: current accepted offline requirements for the example project
lex: "offline" "example-project" requirement -superseded
vec: confirmed constraints for using application content without network access
hyde: The accepted product requirement states which content remains available offline and under what conditions.
```

## Authority-aware retrieval

QMD ranking is merged with structured authority resolved from bundle mappings and frontmatter.

Default routing priority:

```text
active canonical
accepted decisions
reviewed evidence
working knowledge
raw material
superseded history
```

Authority is applied before answer construction, not encoded only as a numeric semantic-score adjustment.

A result without frontmatter remains retrievable. Without a layer mapping or explicit authority, it is unclassified and MUST NOT be assumed canonical.

## Retrieval workflow

1. Resolve project and bundle mappings.
2. Search canonical paths and metadata.
3. Run lexical and/or semantic retrieval.
4. Merge by canonical source path.
5. Exclude denied paths.
6. Exclude superseded knowledge from current answers.
7. Read complete passages or documents.
8. Expand links at depth 1 when needed.
9. assess `sufficient`, `partial`, `stale`, `conflicting` or `absent`.
10. Return paths and source line mappings.

QMD snippets MUST NOT be quoted as final evidence without retrieving their source.

## Fallbacks

If embedding, generation or reranking models are unavailable:

- use QMD BM25/search;
- construct stronger lexical terms;
- preserve authority routing;
- emit a warning;
- do not fail if lexical evidence is sufficient.

If QMD is completely unavailable:

- use Obsidian search when available;
- use bounded direct filesystem search otherwise;
- report degraded semantic recall.

## Resource policy

Initial deployment starts with BM25 only.

Embeddings are enabled after a benchmark demonstrates added value on real questions.

Reranking is enabled only when latency and result quality justify its models and memory footprint.

Caches and models remain outside the vault.

## Required benchmark

Use a corpus from existing workspaces and test at least:

- exact canonical decision;
- semantically related idea without matching tags;
- no-frontmatter note;
- superseded note;
- conflicting sources;
- transcript claim and promoted truth;
- denied note;
- lexical fallback.

Compare raw-index and body-only projection on:

- top-5 recall;
- authority correctness;
- line mapping;
- latency;
- index size;
- frontmatter-induced false positives.

Keep the simpler raw index only if tests show no material quality or confidentiality problem.
