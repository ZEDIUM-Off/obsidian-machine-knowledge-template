#!/usr/bin/env python3
"""Validate exactly what a Git publication would include."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_EXACT = {
    ".github/workflows/privacy.yml",
    ".gitignore",
    ".obsidian/app.json",
    ".obsidian/appearance.json",
    ".obsidian/backlink.json",
    ".obsidian/community-plugins.json",
    ".obsidian/core-plugins.json",
    ".obsidian/plugins/extended-graph/data.json",
    ".obsidian/plugins/notebook-navigator/data.json",
    ".obsidian/plugins/obsidian-style-settings/data.json",
    ".obsidian/templates.json",
    "Atlas.canvas",
    "Atlas.md",
    "Home.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SETUP_PROMPT.md",
    "_dashboards/Current Truth.base",
    "_dashboards/Decisions.base",
    "_dashboards/Evidence.base",
    "_templates/Decision.md",
    "_templates/Evidence.md",
    "_templates/Raw.md",
    "_templates/Truth.md",
    "knowledge/assets/.gitkeep",
    "knowledge/decisions/.gitkeep",
    "knowledge/evidence/.gitkeep",
    "knowledge/index.md",
    "knowledge/raw/.gitkeep",
    "knowledge/truth/.gitkeep",
    "knowledge/work/.gitkeep",
    "plugins.lock.json",
    "scripts/check_public.py",
}
PUBLIC_NOTE_LAYERS = {"truth", "decisions", "work", "evidence", "raw"}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    "absolute Unix user path": re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/"),
    "absolute Windows user path": re.compile(r"\b[A-Z]:\\\\Users\\\\[^\\\s]+", re.I),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "private IPv4": re.compile(
        r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})\b"
    ),
}


def publication_candidates() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(filter(None, result.stdout.decode().split("\0")))


def allowed(rel: str) -> bool:
    parts = Path(rel).parts
    is_public_note = (
        len(parts) >= 3
        and parts[0] == "knowledge"
        and parts[1] in PUBLIC_NOTE_LAYERS
        and rel.endswith(".md")
    )
    return rel in ALLOWED_EXACT or is_public_note


def main() -> int:
    errors: list[str] = []

    try:
        candidates = publication_candidates()
    except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print(f"ÉCHEC — impossible de lire les candidats Git: {exc}", file=sys.stderr)
        return 1

    for rel in candidates:
        path = ROOT / rel
        if not allowed(rel):
            errors.append(f"chemin hors liste blanche: {rel}")
            continue
        if path.is_symlink():
            errors.append(f"symlink interdit: {rel}")
            continue
        if path.stat().st_size > 1_000_000:
            errors.append(f"fichier trop volumineux: {rel}")
            continue

        raw = path.read_bytes()
        if b"\0" in raw:
            errors.append(f"fichier binaire: {rel}")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"texte non UTF-8: {rel}")
            continue

        if path.suffix in {".json", ".canvas"}:
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON invalide: {rel}:{exc.lineno}:{exc.colno}")

        if rel.startswith("knowledge/") and rel.endswith(".md") and rel != "knowledge/index.md":
            if not re.search(r"(?m)^sensitivity:\s*public\s*$", text):
                errors.append(f"note non publique ou sans sensibilité publique: {rel}")

        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} potentiel: {rel}")

    if errors:
        print("ÉCHEC — publication refusée:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"OK — {len(candidates)} fichiers candidats, aucun indicateur privé détecté.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
