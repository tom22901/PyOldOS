"""Tests for the bundled app logic (calculator, notepad, file manager, settings, task manager)."""

import os

import pytest

import main
from main import load_app_from_folder


@pytest.fixture
def wm():
    return main.WindowManager()


class TestCalcApp:
    @pytest.fixture
    def calc(self, wm):
        win = load_app_from_folder("calc", wm)
        return win.app_instance

    def test_display_starts_zero(self, calc):
        assert calc.display.text == "0"

    def test_append_num_replaces_leading_zero(self, calc):
        calc.append_num("1")
        assert calc.display.text == "1"

    def test_append_num_accumulates(self, calc):
        calc.append_num("1")
        calc.append_num("2")
        assert calc.display.text == "12"

    def test_calculate_simple(self, calc):
        calc.display.text = "2+3"
        calc.calculate()
        assert calc.display.text == "5"

    def test_calculate_error_safe(self, calc):
        # the old eval() would have executed this
        calc.display.text = "__import__('os').system('echo HACKED')"
        calc.calculate()
        assert calc.display.text == "Error"

    def test_calculate_division(self, calc):
        calc.display.text = "10/4"
        calc.calculate()
        assert calc.display.text == "2.5"

    def test_calculate_division_by_zero(self, calc):
        calc.display.text = "1/0"
        calc.calculate()
        assert calc.display.text == "Error"

    def test_bind_button_connects_callback(self, calc):
        assert calc.get_element("btn_1").callback is not None


class TestNotepadApp:
    @pytest.fixture
    def notepad(self, wm):
        win = load_app_from_folder("notepad", wm)
        return win.app_instance

    def test_text_area_defaults(self, notepad):
        assert notepad.text_area.get_text() == ""
        assert notepad.text_area.lines == [""]

    def test_insert_and_newline(self, notepad):
        ta = notepad.text_area
        ta.insert_char("a")
        ta.insert_char("b")
        ta.newline()
        ta.insert_char("c")
        assert ta.get_text() == "ab\nc"

    def test_backspace_mid_line(self, notepad):
        ta = notepad.text_area
        for ch in "abc":
            ta.insert_char(ch)
        ta.backspace()
        assert ta.get_text() == "ab"

    def test_backspace_joins_lines(self, notepad):
        ta = notepad.text_area
        for ch in "ab":
            ta.insert_char(ch)
        ta.newline()
        for ch in "cd":
            ta.insert_char(ch)
        ta.cursor_line = 1
        ta.cursor_col = 0
        ta.backspace()
        assert ta.get_text() == "abcd"

    def test_cursor_clamped(self, notepad):
        ta = notepad.text_area
        ta.cursor_line = 99
        ta.cursor_col = 99
        ta.insert_char("x")
        assert ta.lines[0] == "x"

    def test_save_and_reload(self, notepad, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        notepad.txt_file.text = "note.txt"
        ta = notepad.text_area
        ta.set_text("line1\nline2")
        notepad.save_file()
        assert os.path.exists(tmp_path / "note.txt")
        # reopen fresh
        notepad.text_area.set_text("")
        notepad.open_file()
        assert notepad.text_area.get_text() == "line1\nline2"

    def test_new_file_resets(self, notepad):
        notepad.text_area.set_text("something")
        notepad.txt_file.text = "custom.txt"
        notepad.new_file()
        assert notepad.text_area.get_text() == ""
        assert notepad.txt_file.text == "note.txt"


class TestFileManagerApp:
    @pytest.fixture
    def fm(self, wm, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # a small fixture tree
        os.makedirs(tmp_path / "adir")
        (tmp_path / "bfile.txt").write_text("x", encoding="utf-8")
        (tmp_path / "afile.txt").write_text("x", encoding="utf-8")
        win = load_app_from_folder("file_manager", wm)
        return win.app_instance

    def test_refresh_lists_sorted_dirs_first(self, fm, tmp_path):
        fm.refresh_list()
        names = [item[0] for item in fm.file_list_view.items]
        assert names[0] == "adir"  # dir first
        assert "afile.txt" in names
        assert "bfile.txt" in names
        # dirs before files
        is_dirs = [item[1] for item in fm.file_list_view.items]
        assert is_dirs == sorted(is_dirs, reverse=True)

    def test_navigate_into_dir(self, fm, tmp_path):
        fm.on_item_double_click(("adir", True, str(tmp_path / "adir")))
        assert fm.current_path == str(tmp_path / "adir")
        assert "adir" in fm.txt_path.text

    def test_create_file(self, fm, tmp_path):
        fm.txt_new_name.text = "new.txt"
        fm.create_file()
        assert (tmp_path / "new.txt").exists()

    def test_create_dir(self, fm, tmp_path):
        fm.txt_new_name.text = "newdir"
        fm.create_directory()
        assert (tmp_path / "newdir").is_dir()

    def test_create_duplicate_warns(self, fm, tmp_path):
        (tmp_path / "dup.txt").write_text("x", encoding="utf-8")
        fm.txt_new_name.text = "dup.txt"
        fm.create_file()  # should warn, not crash
        assert (tmp_path / "dup.txt").read_text(encoding="utf-8") == "x"


class TestSettingsApp:
    def test_apply_color_changes_system_config(self, wm):
        win = load_app_from_folder("settings", wm)
        app = win.app_instance
        original = main.SYSTEM_CONFIG["bg_color"]
        app.combo_color.selected_index = 2  # 深橄榄绿
        app.apply_color()
        assert main.SYSTEM_CONFIG["bg_color"] == (34, 139, 34)
        main.SYSTEM_CONFIG["bg_color"] = original  # restore

    def test_apply_color_invalid_index_noop(self, wm):
        win = load_app_from_folder("settings", wm)
        app = win.app_instance
        before = main.SYSTEM_CONFIG["bg_color"]
        app.combo_color.selected_index = 99
        app.apply_color()
        assert main.SYSTEM_CONFIG["bg_color"] == before


class TestTaskManagerApp:
    def test_refresh_lists_open_windows(self, wm):
        win = load_app_from_folder("task_manager", wm)
        app = win.app_instance
        app.refresh()
        titles = [t for t, _ in app.task_list.tasks]
        assert win.title in titles

    def test_kill_task_closes_window(self, wm):
        win = load_app_from_folder("task_manager", wm)
        app = win.app_instance
        # make a victim window
        victim = main.Window("victim", 0, 0, 100, 100)
        wm.add_window(victim)
        app.refresh()
        idx = [i for i, (t, _) in enumerate(app.task_list.tasks) if t == "victim"][0]
        app.task_list.selected_index = idx
        app.kill_task()
        assert victim.is_closed is True