"""Tests for JSON-driven window construction and app loading."""

import json
import os

import pytest

import main
from main import build_windows_from_json, load_app_from_folder


@pytest.fixture
def wm():
    return main.WindowManager()


def test_gui_config_loads(REPO_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    wm = main.WindowManager()
    windows = main.build_windows_from_json(os.path.join(REPO_ROOT, "gui_config.json"), wm)
    assert len(windows) >= 1
    assert all(not w.is_closed for w in windows)


def test_build_window_children(wm):
    data = {
        "title": "T",
        "children": [
            {"type": "label", "text": "L", "x": 1, "y": 2},
            {"type": "button", "text": "B", "id": "b1", "x": 3, "y": 4},
            {"type": "checkbox", "text": "C", "x": 5, "y": 6},
            {"type": "textbox", "text": "TB", "x": 7, "y": 8},
            {"type": "combobox", "options": ["a", "b"], "x": 9, "y": 10},
        ],
    }
    win = main.build_window_from_data(data, wm_ref=wm, bind_demo_callbacks=False)
    assert len(win.children) == 5


def test_build_window_demo_callbacks(wm):
    data = {"title": "T", "children": [{"type": "button", "id": "btn_info", "text": "i", "x": 0, "y": 0}]}
    win = main.build_window_from_data(data, wm_ref=wm, bind_demo_callbacks=True)
    btn = win.children[0]
    assert btn.callback is not None


def test_build_window_ignore_unknown_types(wm):
    data = {"title": "T", "children": [{"type": "hologram", "x": 0, "y": 0}]}
    win = main.build_window_from_data(data, wm_ref=wm)
    assert win.children == []


def test_load_app_from_folder_missing_config(wm, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_app_from_folder("nope", wm) is None


def test_load_app_calc(wm):
    win = load_app_from_folder("calc", wm)
    assert win is not None
    assert hasattr(win, "app_instance")
    assert win.app_instance.display is not None
    assert win.app_instance.display.text == "0"


def test_load_app_file_manager(wm):
    win = load_app_from_folder("file_manager", wm)
    assert win is not None
    assert win.app_instance is not None


def test_load_app_settings(wm):
    win = load_app_from_folder("settings", wm)
    assert win is not None
    assert win.app_instance is not None


def test_load_app_notepad(wm):
    win = load_app_from_folder("notepad", wm)
    assert win is not None
    assert win.app_instance is not None
    assert win.app_instance.text_area is not None


def test_load_all_bundled_apps(wm):
    for app in ("browser", "calc", "file_manager", "notepad", "paint", "settings", "task_manager"):
        win = load_app_from_folder(app, wm)
        assert win is not None, f"{app} failed to load"


def test_build_windows_from_json_missing_file(wm, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert build_windows_from_json("missing.json", wm) == []


def test_json_configs_all_valid():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    apps = ["browser", "calc", "file_manager", "notepad", "paint", "settings", "task_manager"]
    for app in apps:
        path = os.path.join(repo, "apps", app, "ui_config.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "title" in data
        assert "children" in data