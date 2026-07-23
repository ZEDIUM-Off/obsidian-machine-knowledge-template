import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("sync_visuals", Path(__file__).with_name("sync_visuals.py"))
sync = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync
SPEC.loader.exec_module(sync)


class SyncVisualsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parents[1] / ".obsidian/plugins"
        for plugin in ("extended-graph", "notebook-navigator"):
            target = self.root / ".obsidian/plugins" / plugin
            target.mkdir(parents=True)
            shutil.copy(source / plugin / "data.json", target / "data.json")
        (self.root / "docs/projects").mkdir(parents=True)
        project_values = {
            "alpha": ("#112233", "box"),
            "beta": ("#445566", "cpu"),
        }
        for project, (color, icon) in project_values.items():
            bundle = self.root / project / "docs"
            bundle.mkdir(parents=True)
            (bundle / "index.md").write_text(
                f'---\nicon: {icon}\ncolor: "{color}"\n---\n# {project}\n'
            )
            (self.root / "docs/projects" / f"{project}.md").write_text(
                f'---\nproject_id: {project}\nproject_path: {project}\nicon: {icon}\ncolor: "{color}"\n---\n# {project}\n'
            )
        self.manifest = {
            "schema": "workspace.projects.v1",
            "projects": [
                {"id": "alpha", "path": "alpha", "color": "#112233", "icon": "box"},
                {"id": "beta", "path": "beta", "color": "#445566", "icon": "cpu"},
            ],
        }
        (self.root / "workspace.projects.json").write_text(json.dumps(self.manifest))

    def tearDown(self):
        self.temp.cleanup()

    def test_projects_generate_matching_states_colors_and_icons(self):
        outputs = sync.expected(self.root)
        extended_path = self.root / ".obsidian/plugins/extended-graph/data.json"
        extended_path.chmod(0o640)
        for path, value in outputs.items():
            sync.atomic_json(path, value)

        self.assertEqual(extended_path.stat().st_mode & 0o777, 0o640)
        extended = outputs[extended_path]
        states = {state["name"]: state for state in extended["states"]}
        self.assertEqual(
            set(states),
            {"Workspace Atlas", "Current Truth", "Human Review", "Agent Surface", "Project · alpha", "Project · beta"},
        )
        self.assertEqual(states["Project · alpha"]["engineOptions"]["search"], 'path:"alpha/"')
        self.assertFalse(any(".pi-subagents" in state["engineOptions"]["search"] for state in states.values()))

        navigator = outputs[self.root / ".obsidian/plugins/notebook-navigator/data.json"]
        self.assertEqual(navigator["folderColors"]["alpha"], "#112233")
        self.assertEqual(navigator["folderIcons"]["beta"], "cpu")
        self.assertEqual(sync.expected(self.root), outputs)

    def test_duplicate_color_is_rejected(self):
        self.manifest["projects"][1]["color"] = "#112233"
        (self.root / "workspace.projects.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            sync.projects(self.root)

    def test_project_path_frontmatter_is_case_sensitive(self):
        note = self.root / "docs/projects/alpha.md"
        note.write_text(note.read_text().replace("project_path: alpha", "project_path: Alpha"))
        with self.assertRaises(ValueError):
            sync.projects(self.root)

    def test_casefolded_path_collision_is_rejected(self):
        bundle = self.root / "Alpha/docs"
        bundle.mkdir(parents=True)
        (bundle / "index.md").write_text('---\nicon: star\ncolor: "#778899"\n---\n')
        (self.root / "docs/projects/gamma.md").write_text(
            '---\nproject_id: gamma\nproject_path: Alpha\nicon: star\ncolor: "#778899"\n---\n'
        )
        self.manifest["projects"].append(
            {"id": "gamma", "path": "Alpha", "color": "#778899", "icon": "star"}
        )
        (self.root / "workspace.projects.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            sync.projects(self.root)


if __name__ == "__main__":
    unittest.main()
