# `kb` CLI

Façade Python pour un vault OKF : recherche authority-first, contrôle d'accès, provenance, Canvas, projections QMD et écritures proposal/apply.

## Installation

```bash
python3 -m pip install .
mkdir -p ~/.config/kb
cp ../../config/kb/config.example.yml ~/.config/kb/config.yml
```

Adapter `vault:` puis lancer :

```bash
kb doctor
kb status
kb truth "current architecture"
kb okf validate
```

Les propositions et locks sont stockés sous `~/.local/state/kb/`; les projections sous `~/.cache/kb/`.
