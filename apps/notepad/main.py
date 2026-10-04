# apps/notepad/main.py

import pygame

from main import (
    COLOR_BLACK,
    COLOR_DARK,
    COLOR_HOVER,
    COLOR_WHITE,
    MessageBox,
    UIElement,
    font,
)


class TextArea(UIElement):
    """多行文本编辑控件：支持光标、换行、退格、滚轮滚动。"""

    LINE_HEIGHT = 18

    def __init__(self, x, y, w, h, align="fill"):
        super().__init__(x, y, w, h, align)
        self.lines = [""]
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0
        self.is_focused = False

    # ---- 文本访问 ----
    def get_text(self):
        return "\n".join(self.lines)

    def set_text(self, text):
        self.lines = text.split("\n") if text else [""]
        self.cursor_line = 0
        self.cursor_col = 0
        self.scroll_offset = 0

    def _ensure_cursor_in_range(self):
        self.cursor_line = max(0, min(self.cursor_line, len(self.lines) - 1))
        self.cursor_col = max(0, min(self.cursor_col, len(self.lines[self.cursor_line])))

    # ---- 编辑操作 ----
    def insert_char(self, ch):
        self._ensure_cursor_in_range()
        line = self.lines[self.cursor_line]
        self.lines[self.cursor_line] = line[:self.cursor_col] + ch + line[self.cursor_col:]
        self.cursor_col += len(ch)

    def newline(self):
        self._ensure_cursor_in_range()
        line = self.lines[self.cursor_line]
        self.lines[self.cursor_line] = line[:self.cursor_col]
        self.lines.insert(self.cursor_line + 1, line[self.cursor_col:])
        self.cursor_line += 1
        self.cursor_col = 0

    def backspace(self):
        self._ensure_cursor_in_range()
        if self.cursor_col > 0:
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col - 1] + line[self.cursor_col:]
            self.cursor_col -= 1
        elif self.cursor_line > 0:
            prev_len = len(self.lines[self.cursor_line - 1])
            self.lines[self.cursor_line - 1] += self.lines[self.cursor_line]
            del self.lines[self.cursor_line]
            self.cursor_line -= 1
            self.cursor_col = prev_len

    def _char_width(self):
        return font.size("中")[0]

    def _clamp_scroll(self):
        content_h = len(self.lines) * self.LINE_HEIGHT
        max_scroll = max(0, content_h - self.rect.h)
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))

    # ---- UI 接口 ----
    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WHITE, r)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.topright)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.bottomleft)
        pygame.draw.line(surface, COLOR_BLACK, r.bottomright, r.topright)
        pygame.draw.line(surface, COLOR_BLACK, r.bottomright, r.bottomleft)

        old_clip = surface.get_clip()
        surface.set_clip(r.clip(old_clip))

        start = self.scroll_offset // self.LINE_HEIGHT
        for i in range(start, len(self.lines)):
            y = r.y + 2 + i * self.LINE_HEIGHT - self.scroll_offset
            if y + self.LINE_HEIGHT > r.bottom:
                break
            txt = font.render(self.lines[i], True, COLOR_BLACK)
            surface.blit(txt, (r.x + 4, y))
            if self.is_focused and i == self.cursor_line:
                caret_x = r.x + 4 + font.size(self.lines[i][:self.cursor_col])[0]
                caret_r = pygame.Rect(caret_x, y, 1, self.LINE_HEIGHT - 4)
                pygame.draw.rect(surface, COLOR_HOVER, caret_r)

        surface.set_clip(old_clip)

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_focused = r.collidepoint(event.pos)
            if self.is_focused:
                rel_y = event.pos[1] - r.y + self.scroll_offset
                line_idx = max(0, min(len(self.lines) - 1, (rel_y - 2) // self.LINE_HEIGHT))
                self.cursor_line = line_idx
                rel_x = event.pos[0] - r.x - 4
                line = self.lines[line_idx]
                col = 0
                width = 0
                for col, ch in enumerate(line):
                    width += font.size(ch)[0]
                    if width > rel_x:
                        break
                else:
                    col = len(line)
                self.cursor_col = max(0, min(col, len(line)))
            return True

        if self.is_focused and event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * self.LINE_HEIGHT
            self._clamp_scroll()
            return True

        if self.is_focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.backspace()
            elif event.key == pygame.K_RETURN:
                self.newline()
            elif event.unicode and event.unicode.isprintable():
                self.insert_char(event.unicode)
            return True
        return False


class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm
        self.txt_file = self.get_child_by_id("txt_file")
        self.btn_new = self.get_child_by_id("btn_new")
        self.btn_open = self.get_child_by_id("btn_open")
        self.btn_save = self.get_child_by_id("btn_save")

        self.text_area = TextArea(12, 40, 420, 260, align="fill")
        self.win.add_child(self.text_area)

        if self.btn_new:
            self.btn_new.callback = self.new_file
        if self.btn_open:
            self.btn_open.callback = self.open_file
        if self.btn_save:
            self.btn_save.callback = self.save_file

    def get_child_by_id(self, cid):
        for child in self.win.children:
            if getattr(child, "id", "") == cid:
                return child
        return None

    def _filename(self):
        return self.txt_file.text.strip() if self.txt_file else "note.txt"

    def new_file(self):
        self.text_area.set_text("")
        if self.txt_file:
            self.txt_file.text = "note.txt"

    def open_file(self):
        name = self._filename()
        if not name:
            MessageBox.show_warning(self.wm, "提示", "请输入文件名！")
            return
        try:
            with open(name, "r", encoding="utf-8") as f:
                self.text_area.set_text(f.read())
        except Exception as e:
            MessageBox.show_error(self.wm, "打开失败", str(e))

    def save_file(self):
        name = self._filename()
        if not name:
            MessageBox.show_warning(self.wm, "提示", "请输入文件名！")
            return
        try:
            with open(name, "w", encoding="utf-8") as f:
                f.write(self.text_area.get_text())
            MessageBox.show_info(self.wm, "保存成功", f"已保存到 {name}")
        except Exception as e:
            MessageBox.show_error(self.wm, "保存失败", str(e))