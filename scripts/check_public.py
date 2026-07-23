#!/usr/bin/env python3
"""Validate the structural files selected for Git publication."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "Atlas.canvas",
    "Atlas.md",
    "Home.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SETUP_PROMPT.md",
    "plugins.lock.json",
    "workspace.projects.json",
}
OBSIDIAN_FILES = {
    ".obsidian/app.json",
    ".obsidian/appearance.json",
    ".obsidian/backlink.json",
    ".obsidian/community-plugins.json",
    ".obsidian/core-plugins.json",
    ".obsidian/graph.json",
    ".obsidian/templates.json",
    ".obsidian/plugins/extended-graph/data.json",
    ".obsidian/plugins/notebook-navigator/data.json",
    ".obsidian/plugins/obsidian-style-settings/data.json",
    ".obsidian/plugins/remote-relevant-tree/LICENSE",
    ".obsidian/plugins/remote-relevant-tree/SOURCE.md",
    ".obsidian/plugins/remote-relevant-tree/main.js",
    ".obsidian/plugins/remote-relevant-tree/manifest.json",
    ".obsidian/plugins/remote-relevant-tree/self-test.js",
}
TEXT_SUFFIXES = {".md", ".base", ".json", ".canvas", ".yml", ".yaml", ".txt", ".py", ".toml", ".js"}
FORBIDDEN_PARTS = {".pi-subagents", "__pycache__", "build", "dist", "node_modules"}
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


def project_roots() -> set[str]:
    data = json.loads((ROOT / "workspace.projects.json").read_text())
    return {str(row["path"]).strip("/") for row in data.get("projects", [])}


def allowed(rel: str, projects: set[str]) -> bool:
    path = Path(rel)
    suffix = path.suffix.lower()
    if FORBIDDEN_PARTS.intersection(path.parts):
        return False
    if rel in ROOT_FILES or rel in OBSIDIAN_FILES or rel == ".github/workflows/checks.yml":
        return True
    if rel == "tools/bin/obsidian-relevant-tree":
        return True
    if path.parts[:1] in [("docs",), (".agents",), (".pi",), ("_templates",)]:
        return suffix in TEXT_SUFFIXES or path.name == ".gitkeep"
    if path.parts[:1] == ("config",):
        return suffix in {".yml", ".yaml", ".txt"}
    if path.parts[:1] == ("scripts",):
        return suffix == ".py"
    if path.parts[:2] == ("tools", "kb"):
        return suffix in {".py", ".toml", ".md"}
    if path.parts[:2] == ("tools", "bin"):
        return suffix == ".md"
    for project in projects:
        if rel == f"{project}/README.md" or rel.startswith(f"{project}/docs/"):
            return suffix == ".md" or path.name == ".gitkeep"
    return False


def main() -> int:
    errors: list[str] = []
    try:
        candidates = publication_candidates()
        projects = project_roots()
    except (subprocess.CalledProcessError, UnicodeDecodeError, OSError, ValueError, KeyError) as exc:
        print(f"ÉCHEC — inventaire Git invalide: {exc}", file=sys.stderr)
        return 1

    for rel in candidates:
        path = ROOT / rel
        if not allowed(rel, projects):
            errors.append(f"chemin hors structure publiée: {rel}")
            continue
        if path.is_symlink():
            errors.append(f"symlink versionné interdit: {rel}")
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
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label} potentiel: {rel}")

    if errors:
        print("ÉCHEC — publication refusée:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"OK — {len(candidates)} fichiers structurels validés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
