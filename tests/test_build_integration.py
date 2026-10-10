"""Slow test: export a tiny real Godot project to Web with the real `godot` binary.
Skipped when `godot` isn't on PATH (or has no matching web export templates)."""

import shutil

import pytest

from art_crit.kinds.godot import export_project

GODOT_BIN = shutil.which("godot")
pytestmark = pytest.mark.skipif(GODOT_BIN is None, reason="godot not on PATH")

PROJECT_GODOT = """; Engine configuration file.
config_version=5

[application]

config/name="Tiny"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")

[rendering]

renderer/rendering_method="gl_compatibility"
"""

MAIN_TSCN = """[gd_scene load_steps=2 format=3]

[sub_resource type="BoxMesh" id="1"]

[node name="Main" type="Node3D"]

[node name="Camera3D" type="Camera3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 5)

[node name="MeshInstance3D" type="MeshInstance3D" parent="."]
mesh = SubResource("1")
"""


@pytest.fixture
def tiny_project(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "project.godot").write_text(PROJECT_GODOT)
    (project_dir / "main.tscn").write_text(MAIN_TSCN)
    return project_dir


def test_export_tiny_project_to_web(tiny_project, tmp_path):
    out_dir = tmp_path / "wasm"
    ok, manifest, error = export_project(GODOT_BIN, tiny_project, out_dir, timeout=180)
    assert ok, error
    assert manifest["threads"] is False
    assert manifest["godot"]
    for name in ("index.html", "index.js", "index.wasm", "index.pck"):
        f = out_dir / name
        assert f.is_file() and f.stat().st_size > 0
    assert (out_dir / "export-manifest.json").is_file()
    # export_presets.cfg is written into the project dir, not the output dir.
    assert (tiny_project / "export_presets.cfg").is_file()
