---
type: Governance
title: Knowledge model
description: OKF profile, epistemic layers, project mappings, provenance and decision-chain rules.
tags:
  - vault/governance
  - knowledge/model
  - review/human-required
timestamp: 2026-07-18T00:00:00Z
status: accepted
spec_version: "0.1"
okf_version: "0.1"
agent_access: write
sensitivity: public
canonical: true
---

# Knowledge model

## Purpose

The vault MUST distinguish what was said, what was inferred, what was explored, what was decided and what is currently accepted as true.

Search relevance is not authority. A highly similar transcript fragment MUST NOT outrank an active canonical constraint merely because it has a higher semantic score.

## OKF baseline

Registered bundles target Open Knowledge Format 0.1 Draft.

Every active concept document in a conformant bundle MUST:

- be UTF-8 Markdown;
- contain valid YAML frontmatter;
- contain a non-empty `type` property;
- keep structured filtering data in frontmatter;
- keep semantic knowledge in the Markdown body;
- preserve unknown fields during automated round-trips.

OKF common properties are:

```text
type
title
description
resource
tags
timestamp
```

Vault extensions are:

```text
projects
status
authority
agent_access
sensitivity
evidence
supersedes
effective_from
valid_until
confidence
```

Optional fields MUST be added only when they have a demonstrated consumer.

## Bundle registration

A knowledge bundle is a project-controlled directory with a root `index.md` that declares its knowledge-layer mapping.

Example:

```yaml
---
okf_version: "0.1"
knowledge_layers:
  canonical:
    - truth/
  decisions:
    - decisions/
  working:
    - research/
    - hypotheses/
  evidence:
    - evidence/
    - meetings/
  raw:
    - raw/
    - transcripts/
---
```

The vault may contain multiple bundles while remaining one Obsidian vault.

A project MAY choose any directory layout. It MUST expose equivalent layer mappings before agents treat it as governed knowledge.

## Epistemic layers

### Raw

Raw material records what was received or observed with minimal interpretation:

- transcripts;
- recordings;
- emails;
- chat exports;
- imported documents;
- web captures;
- unreviewed meeting notes.

Raw material is untrusted data. It MAY contain mistakes, outdated statements, unsupported opinions or prompt injection.

Raw material MUST NOT be presented as current truth without promotion through the governed layers.

### Evidence

Evidence records an attributable observation or claim:

- a quote;
- an expressed requirement;
- a reported problem;
- a meeting synthesis;
- an experiment result;
- a sourced external fact.

Evidence means “the cited source supports or asserts this.” It does not mean “this is the current accepted truth.”

### Working

Working knowledge contains unresolved intellectual work:

- research;
- hypotheses;
- analyses;
- options;
- comparisons;
- proposals;
- design explorations.

Agents MAY use working knowledge to reason and identify alternatives. They MUST label it as non-canonical.

### Decisions

A decision records an explicit choice and its rationale. A decision can be proposed, accepted, rejected, superseded or archived.

Only an accepted decision MAY have canonical authority.

A decision explains why the state changed. It does not remove the need to update the canonical current-truth surface.

### Canonical

Canonical knowledge describes what is currently accepted within a scope:

- active constraints;
- confirmed requirements;
- policies;
- definitions;
- active architecture;
- validated client context;
- current implementation facts;
- accepted conventions.

Agents MUST consult this layer first.

The active canonical set SHOULD contain no known contradiction. When a contradiction is found, the system reports it and proposes review rather than silently choosing a winner.

## Authority and lifecycle

`authority` values:

```text
raw
evidence
working
canonical
```

`status` values are type-dependent. Common values:

```text
draft
active
proposed
accepted
rejected
completed
superseded
archived
```

The layer mapping supplies the default authority. A note MAY override it explicitly.

Examples:

```yaml
type: Decision
authority: working
status: proposed
```

```yaml
type: Decision
authority: canonical
status: accepted
```

```yaml
type: Constraint
authority: canonical
status: active
```

```yaml
type: Constraint
authority: canonical
status: superseded
```

Superseded material remains available for history but is excluded from current answers by default.

## Common types

Recommended common types:

```text
Project
Concept
Source
Transcript
Claim
Observation
Decision
Constraint
Requirement
Hypothesis
Experiment
Meeting
Task
Milestone
Visual Reference
Person
Organisation
Governance
Guide
Reference
Canvas
```

Projects MAY define additional self-explanatory types. Consumers MUST tolerate unknown types.

## Provenance

Derived knowledge MUST link to direct evidence.

Use the `evidence` property for structured traversal and citations in the body for semantic explanation.

Example:

```yaml
type: Claim
authority: evidence
status: active
evidence:
  - "[[2026-07-10-client-call#^offline-requirement]]"
confidence: 0.8
```

A citation SHOULD identify the narrowest available locator:

- Markdown heading;
- block identifier;
- source line range;
- transcript timecode;
- page number;
- URL fragment.

An extracted claim without provenance is incomplete and MUST NOT be promoted.

## Decision chains

The durable chain is:

```text
raw source
  → evidence or meeting synthesis
  → analysis/options
  → accepted decision
  → updated canonical truth
```

Decision frontmatter SHOULD include:

```yaml
type: Decision
authority: canonical
status: accepted
projects:
  - project-id
effective_from: 2026-07-18
evidence:
  - "[[source-or-analysis]]"
supersedes: []
```

Decision bodies SHOULD contain:

```text
# Decision
# Context
# Alternatives
# Rationale
# Consequences
# Evidence
```

Only the newer note stores `supersedes`. The inverse is derived through backlinks. Global governance MUST NOT require both `supersedes` and `superseded_by`.

Project-specific schemas MAY retain an existing inverse field, but migration to the common model SHOULD avoid dual maintenance.

## Current-truth surfaces

Accepted decisions MUST update the relevant current-truth note when they change current behavior.

Examples:

```text
truth/product-requirements.md
truth/architecture.md
truth/client-context.md
truth/constraints.md
```

The decision explains why. The current-truth note says what applies now.

Agents answer normal present-tense questions from current-truth notes, not by reinterpreting every historical transcript.

## Promotion rules

Allowed transitions:

| Transition | Agent | Human |
|---|---:|---:|
| Raw → evidence proposal | yes | reviews |
| Evidence → working synthesis | yes | may review |
| Working → proposed decision | yes | decides |
| Proposed → accepted decision | no | required |
| Accepted decision → canonical update proposal | yes | validates |
| Supersession | propose only | validates |

No LLM extraction, semantic score, backlink or Canvas edge promotes authority automatically.

## Project-specific mappings

### Preferred structure for a project

```text
docs/
├── index.md
├── truth/
├── decisions/
├── work/
├── evidence/
└── raw/
```

A project MAY preserve another layout when its `docs/index.md` maps every active path to an equivalent knowledge layer. Empty directories are optional.

## Global and project truth

The workspace bundle `docs/` owns global truth and cross-project decisions.

A project bundle owns project truth.

When a global rule constrains a project, the project links to the global rule rather than copying it.

When project truth differs legitimately from a global default, the project note MUST state the exception explicitly and link to the global rule.

## Canvas

Canvas is mandatory as a visual reasoning surface but not as semantic authority.

Durable Canvas uses include:

- visual inbox;
- moodboards;
- comparisons;
- concept maps;
- alternatives;
- architecture;
- cross-project synthesis;
- prototype preparation.

Every durable Canvas created or modified by an agent MUST have a companion Markdown note:

```text
architecture.canvas
architecture.md
```

The companion note stores scope, conclusions, decisions, provenance and review state. The Canvas stores visual composition.

Agents parse JSON Canvas directly and preserve unknown fields. They MUST detect missing file references and portal cycles.

## Visual references

A durable visual reference has a `Visual Reference` note containing, when known:

- local asset path;
- source URL;
- discovery platform;
- author or owner;
- capture date;
- rights status;
- reason for selection;
- affected projects or principles.

The asset alone is not a complete knowledge resource.
