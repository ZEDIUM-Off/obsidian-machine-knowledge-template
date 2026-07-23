#!/usr/bin/env python3
"""Synchronize project registry into Obsidian visual configuration."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
LAYERS = ("truth", "decisions", "work", "evidence", "raw")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def frontmatter_scalar(path: Path, key: str) -> str:
    if not path.is_file():
        raise ValueError(f"missing project note: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter: {path}")
    end = text.find("\n---", 4)
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text[4:end]) if end >= 0 else None
    if not match:
        raise ValueError(f"missing {key} in {path}")
    return match.group(1).strip().strip("\\\"'")


def projects(root: Path) -> list[dict[str, str]]:
    data = load_json(root / "workspace.projects.json")
    if data.get("schema") != "workspace.projects.v1" or not isinstance(data.get("projects"), list):
        raise ValueError("workspace.projects.json: invalid schema")

    rows: list[dict[str, str]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    colors: set[str] = set()
    basenames: set[str] = set()
    for raw in data["projects"]:
        if not isinstance(raw, dict):
            raise ValueError("project entries must be objects")
        row = {key: str(raw.get(key, "")).strip() for key in ("id", "path", "color", "icon")}
        path = Path(row["path"])
        if not PROJECT_ID.fullmatch(row["id"]):
            raise ValueError(f"invalid project id: {row['id']!r}")
        if (
            path.is_absolute()
            or ".." in path.parts
            or not row["path"]
            or row["path"].startswith(".")
            or path.as_posix() != row["path"]
        ):
            raise ValueError(f"invalid project path: {row['path']!r}")
        if not (root / path).is_dir():
            raise ValueError(f"missing project directory: {row['path']}")
        if not COLOR.fullmatch(row["color"]):
            raise ValueError(f"invalid color for {row['id']}: {row['color']!r}")
        if not row["icon"]:
            raise ValueError(f"missing icon for {row['id']}")
        basename = path.name
        identity = row["id"].casefold()
        path_key = row["path"].casefold()
        basename_key = basename.casefold()
        if identity in ids or path_key in paths or row["color"].lower() in colors or basename_key in basenames:
            raise ValueError(f"duplicate id, path, color or folder name: {row['id']}")
        registry_note = root / "docs/projects" / f'{row["id"]}.md'
        bundle_index = root / path / "docs/index.md"
        expected_fields = {
            registry_note: {
                "project_id": row["id"],
                "project_path": row["path"],
                "icon": row["icon"],
                "color": row["color"],
            },
            bundle_index: {"icon": row["icon"], "color": row["color"]},
        }
        for note, fields in expected_fields.items():
            for key, expected in fields.items():
                actual = frontmatter_scalar(note, key)
                matches = actual.lower() == expected.lower() if key == "color" else actual == expected
                if not matches:
                    raise ValueError(f"{note}: {key} must equal {expected!r}")
        ids.add(identity)
        paths.add(path_key)
        colors.add(row["color"].lower())
        basenames.add(basename_key)
        rows.append(row)
    return sorted(rows, key=lambda row: row["id"])


def rgb(color: str) -> int:
    return int(color.removeprefix("#"), 16)


def color_group(query: str, color: str) -> dict[str, Any]:
    return {"query": query, "color": {"a": 1, "rgb": rgb(color)}}


def state(identifier: str, name: str, search: str, groups: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": identifier,
        "name": name,
        "engineOptions": {
            "colorGroups": deepcopy(groups),
            "search": search,
            "hideUnresolved": True,
            "showAttachments": False,
            "showOrphans": True,
            "showTags": False,
            "localBacklinks": True,
            "localForelinks": True,
            "localInterlinks": False,
            "localJumps": 1,
            "lineSizeMultiplier": 1.2,
            "nodeSizeMultiplier": 1.15,
            "showArrow": False,
            "textFadeMultiplier": 0,
            "centerStrength": 0,
            "linkDistance": 160,
            "linkStrength": 0.8,
            "repelStrength": 14,
        },
        "toggleTypes": {"folder": [], "tag": [], "link": []},
        "logicTypes": {"folder": "OR", "tag": "OR", "link": "OR"},
        "pinNodes": {},
        "hiddenLegendRows": [],
        "collapsedLegendRows": [],
        "enableLayers": False,
        "currentLayerLevel": 0,
    }


def expected(root: Path) -> dict[Path, dict[str, Any]]:
    rows = projects(root)
    extended_path = root / ".obsidian/plugins/extended-graph/data.json"
    navigator_path = root / ".obsidian/plugins/notebook-navigator/data.json"
    extended = load_json(extended_path)
    navigator = load_json(navigator_path)

    project_groups = [
        color_group(f'path:"{row["path"].rstrip("/")}/"', row["color"])
        for row in rows
    ]
    agent_groups = [
        color_group('path:".agents/"', "#f59e0b"),
        color_group('path:".pi/"', "#8b5cf6"),
        color_group('path:".agents-global/"', "#06b6d4"),
        color_group('path:".pi-global/"', "#3b82f6"),
    ]
    states = [
        state("workspace-atlas", "Workspace Atlas", "", project_groups),
        state("current-truth", "Current Truth", "[authority:canonical] -[status:superseded]", project_groups),
        state("human-review", "Human Review", "tag:#review/human-required", project_groups),
        state(
            "agent-surface",
            "Agent Surface",
            '(path:".agents/" OR path:".pi/" OR path:".agents-global/" OR path:".pi-global/")',
            agent_groups,
        ),
    ]
    states.extend(
        state(
            f'project-{row["id"]}',
            f'Project · {row["id"]}',
            f'path:"{row["path"].rstrip("/")}/"',
            [color_group(f'path:"{row["path"].rstrip("/")}/"', row["color"])],
        )
        for row in rows
    )

    extended["states"] = states
    extended["startingStateID"] = "workspace-atlas"
    extended["physicalFolderTree"] = True
    extended["folderShowFullPath"] = False
    extended["iconProperties"] = ["icon"]
    extended["usePropertiesForName"] = ["title"]
    extended["useParentIcon"] = True
    extended["useIconColorForBackgroud"] = True
    extended.setdefault("enableFeatures", {}).setdefault("graph", {}).update(
        {"auto-enabled": True, "folders": True, "icons": True, "names": True}
    )

    fixed_icons = {
        "docs": "book-open",
        ".agents": "bot",
        ".pi": "workflow",
        "_templates": "file-plus-2",
    }
    fixed_colors = {
        "docs": "#d9a337",
        ".agents": "#f59e0b",
        ".pi": "#8b5cf6",
        "_templates": "#64748b",
    }
    navigator["folderIcons"] = fixed_icons | {Path(row["path"]).name: row["icon"] for row in rows}
    navigator["folderColors"] = fixed_colors | {Path(row["path"]).name: row["color"] for row in rows}
    navigator["vaultTitle"] = "Machine Knowledge Workspace"

    graph = {
        "collapse-filter": False,
        "search": "",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": True,
        "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": project_groups,
        "collapse-display": True,
        "showArrow": False,
        "textFadeMultiplier": 0,
        "nodeSizeMultiplier": 1.15,
        "lineSizeMultiplier": 1.2,
        "collapse-forces": True,
        "centerStrength": 0,
        "repelStrength": 14,
        "linkStrength": 0.8,
        "linkDistance": 160,
    }
    return {extended_path: extended, navigator_path: navigator, root / ".obsidian/graph.json": graph}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = expected(root)

    if args.check:
        drift = [path.relative_to(root).as_posix() for path, value in outputs.items() if not path.exists() or load_json(path) != value]
        if drift:
            print("Visual configuration drift:")
            for path in drift:
                print(f"- {path}")
            return 1
        print(f"Visual configuration OK: {len(projects(root))} project state(s).")
        return 0

    for path, value in outputs.items():
        atomic_json(path, value)
    print(f"Visual configuration synchronized: {len(projects(root))} project state(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
