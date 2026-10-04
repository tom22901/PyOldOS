"""Tests for Window, WindowManager, Taskbar, Menu, and MessageBox."""

import pygame
import pytest

from main import (
    DEFAULT_MENU_BAR,
    HEIGHT,
    TASKBAR_HEIGHT,
    WIDTH,
    Button,
    Label,
    Menu,
    MessageBox,
    Taskbar,
    TextBox,
    Window,
)


@pytest.fixture
def win():
    return Window("Test", 100, 100, 300, 200)


@pytest.fixture
def click():
    def make(button=1, pos=(0, 0), etype=pygame.MOUSEBUTTONDOWN):
        return type("Evt", (), {"type": etype, "button": button, "pos": pos})()

    return make


class TestWindow:
    def test_initial_state(self, win):
        assert win.is_closed is False
        assert win.is_minimized is False
        assert win.is_maximized is False
        assert win.title == "Test"

    def test_add_child_updates_layout(self, win):
        win.add_child(Label("hi", 5, 5))
        assert len(win.children) == 1

    def test_close_button(self, win, click):
        evt = click(pos=(win.close_btn_rect.center))
        assert win.handle_event(evt, True) is True
        assert win.is_closed is True

    def test_minimize_button(self, win, click):
        evt = click(pos=(win.min_btn_rect.center))
        assert win.handle_event(evt, True) is True
        assert win.is_minimized is True

    def test_maximize_toggle(self, win, click):
        evt = click(pos=(win.max_btn_rect.center))
        assert win.handle_event(evt, True) is True
        assert win.is_maximized is True
        assert win.rect.w == WIDTH
        assert win.rect.h == HEIGHT - TASKBAR_HEIGHT
        # undo
        win.handle_event(click(pos=(win.max_btn_rect.center)), True)
        assert win.is_maximized is False

    def test_drag_moves_window(self, win, click):
        # press on title bar center (300 wide → center x = 250): drag_offset = rect.pos - click.pos
        press_pos = win.title_bar_rect.center  # (250, 111)
        assert win.handle_event(click(pos=press_pos), True) is True
        assert win.is_dragging is True
        # motion to (160, 120): new x = 160 + (100-250) = 10, new y = 120 + (100-111) = 109
        motion = type("Evt", (), {"type": pygame.MOUSEMOTION, "pos": (160, 120)})()
        win.handle_event(motion, True)
        assert win.rect.x == 10
        assert win.rect.y == 109


class TestWindowManager:
    def test_add_and_top(self, wm):
        w1 = Window("1", 0, 0, 100, 100)
        w2 = Window("2", 0, 0, 100, 100)
        wm.add_window(w1)
        wm.add_window(w2)
        assert wm.get_top_window() is w2

    def test_bring_to_front(self, wm):
        w1 = Window("1", 0, 0, 100, 100)
        w2 = Window("2", 0, 0, 100, 100)
        wm.add_window(w1)
        wm.add_window(w2)
        wm.bring_to_front(w1)
        assert wm.get_top_window() is w1

    def test_closed_windows_excluded_from_top(self, wm):
        w1 = Window("1", 0, 0, 100, 100)
        w2 = Window("2", 0, 0, 100, 100)
        wm.add_window(w2)
        wm.add_window(w1)
        w1.is_closed = True
        assert wm.get_top_window() is w2

    def test_minimized_window_not_top(self, wm):
        w1 = Window("1", 0, 0, 100, 100)
        wm.add_window(w1)
        w1.is_minimized = True
        assert wm.get_top_window() is None


class TestTaskbar:
    def test_creation(self, wm):
        taskbar = Taskbar(WIDTH, HEIGHT, [])
        assert taskbar.rect.h == 30
        assert taskbar.start_btn_rect.x == 2

    def test_app_button_restores_minimized(self, wm, click):
        taskbar = Taskbar(WIDTH, HEIGHT, [])
        w1 = Window("App", 0, 0, 100, 100)
        wm.add_window(w1)
        w1.is_minimized = True
        taskbar.app_buttons = []
        # simulate draw gathering buttons
        surface = pygame.Surface((WIDTH, HEIGHT))
        taskbar.draw(surface, wm.windows, wm.get_top_window(), "admin", "admin")
        assert len(taskbar.app_buttons) == 1
        btn_rect, win = taskbar.app_buttons[0]
        evt = click(pos=btn_rect.center)
        assert taskbar.handle_event(evt, lambda a: None, wm) is True
        assert win.is_minimized is False

    def test_start_menu_toggle(self, wm, click):
        taskbar = Taskbar(WIDTH, HEIGHT, [{"label": "X", "action": "sys_shutdown"}])
        evt = click(pos=taskbar.start_btn_rect.center)
        assert taskbar.handle_event(evt, lambda a: None, wm) is True
        assert taskbar.start_menu is not None
        taskbar.handle_event(click(pos=taskbar.start_btn_rect.center), lambda a: None, wm)
        assert taskbar.start_menu is None


class TestMenu:
    def test_click_action_fires_and_closes(self, click):
        fired = []
        menu = Menu([{"label": "A", "action": "act_a"}], 0, 0)
        menu.handle_event(click(pos=(10, 10)), fired.append, lambda: None)
        assert fired == ["act_a"]

    def test_submenu_click_passthrough(self, click):
        fired = []
        menu = Menu([{"label": "A", "action": None, "submenu": [{"label": "B", "action": "act_b"}]}], 0, 0)
        # expand submenu by simulating hover state
        menu.sub_menu = Menu([{"label": "B", "action": "act_b"}], 140, 0)
        assert menu.handle_event(click(pos=(10, 10)), fired.append, lambda: None) is True
        assert fired == []

    def test_click_outside_root_closes(self, click):
        closed = []
        menu = Menu([{"label": "A", "action": "act_a"}], 0, 0)
        menu.handle_event(click(pos=(500, 500)), lambda a: None, lambda: closed.append(1))
        assert closed == [1]

    def test_position_clamped_to_screen(self):
        menu = Menu([{"label": "A"}], WIDTH - 10, HEIGHT - 5)
        assert menu.rect.right <= WIDTH
        assert menu.rect.bottom <= HEIGHT


class TestMessageBox:
    def test_show_info_creates_window(self, wm):
        MessageBox.show_info(wm, "T", "Msg")
        assert len(wm.windows) == 1
        assert wm.windows[0].is_closed is False

    def test_show_yes_no_yes_callback(self, wm):
        clicked = []
        MessageBox.show_yes_no(wm, "T", "Q", on_yes=lambda: clicked.append(1))
        win = wm.windows[0]
        # the "yes" button is index 0; call its callback
        cb = win.children[-2].callback  # last two are buttons
        cb()
        assert clicked == [1]

    def test_show_input_submit(self, wm):
        results = []
        MessageBox.show_input(wm, "T", "P", on_submit=lambda t: results.append(t))
        win = wm.windows[0]
        tb = [c for c in win.children if isinstance(c, TextBox)][0]
        tb.text = "hello"
        btn = [c for c in win.children if isinstance(c, Button)][0]
        btn.callback()
        assert results == ["hello"]
        assert win.is_closed is True


class TestDefaultMenuBar:
    def test_default_menu_bar_shape(self):
        assert DEFAULT_MENU_BAR[0]["label"] == "文件"
        assert DEFAULT_MENU_BAR[2]["label"] == "帮助"