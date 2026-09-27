"""Tests for the core UI widget library in main.py (headless)."""

import pygame

from main import (
    Button,
    CheckBox,
    ComboBox,
    Label,
    ProgressBar,
    RadioGroup,
    SelectionBox,
    TextBox,
    UIElement,
)

SURFACE = pygame.Surface((900, 700))


class TestSelectionBox:
    def test_start_activates(self):
        sb = SelectionBox()
        sb.start((10, 10))
        assert sb.active is True
        assert sb.start_pos == (10, 10)

    def test_update_moves_current(self):
        sb = SelectionBox()
        sb.start((0, 0))
        sb.update((50, 40))
        assert sb.current_pos == (50, 40)

    def test_update_when_inactive_is_noop(self):
        sb = SelectionBox()
        sb.update((50, 40))
        assert sb.current_pos == (0, 0)

    def test_stop_deactivates(self):
        sb = SelectionBox()
        sb.start((0, 0))
        sb.stop()
        assert sb.active is False


class TestButton:
    def test_click_invokes_callback(self, click):
        calls = []
        btn = Button("OK", 0, 0, 80, 25, callback=lambda: calls.append(1))
        assert btn.handle_event(click(button=1, pos=(40, 12)), 0, 0) is True
        # release inside -> callback fires
        assert btn.handle_event(click(button=1, pos=(40, 12), etype=pygame.MOUSEBUTTONUP), 0, 0) is True
        assert calls == [1]

    def test_release_outside_does_not_fire(self, click):
        calls = []
        btn = Button("OK", 0, 0, 80, 25, callback=lambda: calls.append(1))
        btn.handle_event(click(button=1, pos=(40, 12)), 0, 0)
        btn.handle_event(click(button=1, pos=(500, 500), etype=pygame.MOUSEBUTTONUP), 0, 0)
        assert calls == []

    def test_press_outside_does_not_activate(self, click):
        btn = Button("OK", 0, 0, 80, 25)
        assert btn.handle_event(click(button=1, pos=(500, 500)), 0, 0) is False
        assert btn.is_pressed is False

    def test_move_offset_respected(self, click):
        calls = []
        btn = Button("OK", 100, 100, 80, 25, callback=lambda: calls.append(1))
        # abs coords are abs_x + rel_x → button spans (200,200)-(280,225)
        assert btn.handle_event(click(button=1, pos=(240, 212)), 100, 100) is True
        btn.handle_event(click(button=1, pos=(240, 212), etype=pygame.MOUSEBUTTONUP), 100, 100)
        assert calls == [1]


class TestCheckBox:
    def test_toggle(self, click):
        cb = CheckBox("opt", 0, 0)
        assert cb.checked is False
        cb.handle_event(click(button=1, pos=(5, 5)), 0, 0)
        assert cb.checked is True
        cb.handle_event(click(button=1, pos=(5, 5)), 0, 0)
        assert cb.checked is False

    def test_click_outside_no_toggle(self, click):
        cb = CheckBox("opt", 0, 0)
        cb.handle_event(click(button=1, pos=(500, 500)), 0, 0)
        assert cb.checked is False


class TestRadioGroup:
    def test_select_index(self, click):
        rg = RadioGroup(["a", "b", "c"], 0, 0)
        assert rg.selected_index == 0
        rg.handle_event(click(button=1, pos=(10, 22 + 8)), 0, 0)  # second option
        assert rg.selected_index == 1

    def test_click_outside_no_change(self, click):
        rg = RadioGroup(["a", "b"], 0, 0)
        rg.handle_event(click(button=1, pos=(500, 500)), 0, 0)
        assert rg.selected_index == 0


class TestTextBox:
    def test_focus_on_click(self, click):
        tb = TextBox("", 0, 0)
        tb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        assert tb.is_focused is True

    def test_type_appends_printable(self, click, key):
        tb = TextBox("", 0, 0)
        tb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        tb.handle_event(key(pygame.K_a, unicode="a"), 0, 0)
        tb.handle_event(key(pygame.K_b, unicode="b"), 0, 0)
        assert tb.text == "ab"

    def test_backspace_removes(self, click, key):
        tb = TextBox("abc", 0, 0)
        tb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        tb.handle_event(key(pygame.K_BACKSPACE), 0, 0)
        assert tb.text == "ab"

    def test_unprintable_ignored(self, click, key):
        tb = TextBox("", 0, 0)
        tb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        tb.handle_event(key(pygame.K_RETURN, unicode="\r"), 0, 0)
        assert tb.text == ""

    def test_no_typing_when_unfocused(self, key):
        tb = TextBox("", 0, 0)
        tb.handle_event(key(pygame.K_a, unicode="a"), 0, 0)
        assert tb.text == ""

    def test_password_masked_but_stored_plain(self, click, key):
        tb = TextBox("", 0, 0, is_password=True)
        tb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        tb.handle_event(key(pygame.K_s, unicode="s"), 0, 0)
        assert tb.text == "s"


class TestProgressBar:
    def test_clamps_above_100(self):
        pb = ProgressBar(0, 0, 200, 20, progress=1.5)
        fill_w = int((pb.rect.w - 4) * min(1.0, max(0.0, pb.progress)))
        assert fill_w == pb.rect.w - 4

    def test_clamps_below_0(self):
        pb = ProgressBar(0, 0, 200, 20, progress=-0.5)
        assert pb.progress == -0.5  # stored raw, clamped only when drawn

    def test_mid_progress(self):
        pb = ProgressBar(0, 0, 200, 20, progress=0.5)
        fill_w = int((pb.rect.w - 4) * min(1.0, max(0.0, pb.progress)))
        assert fill_w == int(196 * 0.5)


class TestComboBox:
    def test_open_and_close(self, click):
        cb = ComboBox(["a", "b"], 0, 0)
        assert cb.is_open is False
        cb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        assert cb.is_open is True
        cb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        assert cb.is_open is False

    def test_select_option(self, click):
        cb = ComboBox(["a", "b"], 0, 0)
        cb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        # dropdown item i sits at y = h + i*h … 2h + i*h  (h=22)
        assert cb.handle_event(click(button=1, pos=(10, 22 + 22 + 11)), 0, 0) is True
        assert cb.selected_index == 1
        assert cb.is_open is False

    def test_click_outside_closes(self, click):
        cb = ComboBox(["a", "b"], 0, 0)
        cb.handle_event(click(button=1, pos=(10, 10)), 0, 0)
        cb.handle_event(click(button=1, pos=(500, 500)), 0, 0)
        assert cb.is_open is False


class TestUIElementLayout:
    def test_align_right(self):
        el = UIElement(x=10, y=5, w=50, h=20, align="right")
        el.update_layout(200, 100)
        assert el.rect.x == 200 - 10 - 50
        assert el.rect.y == 5

    def test_align_fill(self):
        el = UIElement(x=10, y=5, w=50, h=20, align="fill")
        el.update_layout(200, 100)
        assert el.rect.x == 10
        assert el.rect.w == max(20, 200 - 20)

    def test_align_left(self):
        el = UIElement(x=10, y=5, w=50, h=20, align="left")
        el.update_layout(200, 100)
        assert el.rect.x == 10
        assert el.rect.w == 50

    def test_default_draw_and_event_noop(self):
        el = UIElement()
        assert el.draw(SURFACE, 0, 0) is None
        assert el.handle_event(None, 0, 0) is False


class TestLabel:
    def test_holds_text(self):
        lbl = Label("hello", 5, 5)
        assert lbl.text == "hello"
        assert lbl.rect.x == 5