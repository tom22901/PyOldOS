import hashlib
import importlib.util
import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime

import pygame

# ==========================================
# 0. 数据库与用户鉴权 (SQLite)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PYOLDOS_DB", os.path.join(BASE_DIR, "system.db"))


def hash_password(password, salt=None):
    """以加盐 SHA-256 哈希保存密码，不使用明文。"""
    if salt is None:
        salt = secrets.token_hex(8)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(stored, password):
    """校验密码；兼容旧版本数据库中的明文记录。"""
    if "$" in stored:
        salt, digest = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == digest
    return stored == password


def init_db(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL  -- 'admin' 或 'user'
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("admin", hash_password("123456"), "admin"))
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("user", hash_password("123456"), "user"))
    conn.commit()
    conn.close()


def verify_login(username, password, db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, password FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        return None
    role, stored_password = result
    return role if verify_password(stored_password, password) else None

# ==========================================
# 1. 全局配置与状态定义
# ==========================================
SYSTEM_CONFIG = {
    "bg_color": (0, 128, 128)
}

STATE_BOOT = "BOOT"
STATE_LOGIN = "LOGIN"
STATE_DESKTOP = "DESKTOP"

current_state = STATE_BOOT
current_user = None
current_role = None

pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Retro Desktop System")


def set_system_resolution(new_w, new_h):
    global WIDTH, HEIGHT, screen, taskbar
    WIDTH, HEIGHT = new_w, new_h
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    taskbar.rect.y = HEIGHT - TASKBAR_HEIGHT
    taskbar.start_btn_rect.y = HEIGHT - TASKBAR_HEIGHT + 2
    for win in wm.windows:
        win.rect.x = min(win.rect.x, WIDTH - win.rect.w)
        win.rect.y = min(win.rect.y, HEIGHT - TASKBAR_HEIGHT - win.rect.h)


def lerp(start, end, factor=0.25):
    return start + (end - start) * factor


def get_chinese_font(size=14):
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/msyh.ttc"
    ]
    for path in font_paths:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("arial", size)


font = get_chinese_font(14)
font_small = get_chinese_font(12)
font_large = get_chinese_font(26)

COLOR_BG = (0, 128, 128)
COLOR_WIN_BG = (192, 192, 192)
COLOR_TITLE_ACTIVE = (0, 0, 128)
COLOR_TITLE_INACTIVE = (128, 128, 128)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (128, 128, 128)
COLOR_BLACK = (0, 0, 0)
COLOR_HOVER = (0, 0, 128)
COLOR_PROGRESS = (0, 0, 128)
COLOR_SELECTION = (0, 120, 215, 100)

TASKBAR_HEIGHT = 30
TOOLBAR_HEIGHT = 20  # 工具栏默认高度

# 默认兼容菜单栏配置
DEFAULT_MENU_BAR = [
    {
        "label": "文件",
        "submenu": [
            {"label": "新建", "action": "menu_file_new"},
            {"label": "打开", "action": "menu_file_open"},
            {"label": "保存", "action": "menu_file_save"},
            {"label": "退出", "action": "menu_file_exit"}
        ]
    },
    {
        "label": "编辑",
        "submenu": [
            {"label": "撤销", "action": "menu_edit_undo"},
            {"label": "剪切", "action": "menu_edit_cut"},
            {"label": "复制", "action": "menu_edit_copy"},
            {"label": "粘贴", "action": "menu_edit_paste"}
        ]
    },
    {
        "label": "帮助",
        "submenu": [
            {"label": "查看帮助", "action": "menu_help_view"},
            {"label": "关于", "action": "menu_help_about"}
        ]
    }
]


# ==========================================
# 2. 桌面鼠标框选组件
# ==========================================
class SelectionBox:
    def __init__(self):
        self.active = False
        self.start_pos = (0, 0)
        self.current_pos = (0, 0)

    def start(self, pos):
        self.active = True
        self.start_pos = pos
        self.current_pos = pos

    def update(self, pos):
        if self.active:
            self.current_pos = pos

    def stop(self):
        self.active = False

    def draw(self, surface):
        if not self.active:
            return
        x = min(self.start_pos[0], self.current_pos[0])
        y = min(self.start_pos[1], self.current_pos[1])
        w = abs(self.start_pos[0] - self.current_pos[0])
        h = abs(self.start_pos[1] - self.current_pos[1])

        if w > 0 and h > 0:
            select_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            select_surf.fill(COLOR_SELECTION)
            surface.blit(select_surf, (x, y))
            pygame.draw.rect(surface, (0, 120, 215), (x, y, w, h), 1)


# ==========================================
# 3. 多级上下文右键与开始菜单
# ==========================================
class Menu:
    ITEM_HEIGHT = 24
    MENU_WIDTH = 130

    def __init__(self, items, x, y, is_root=True, upward=False):
        self.items = items
        self.is_root = is_root
        self.upward = upward
        self.active_sub_index = None
        self.sub_menu = None
        self.target_h = len(items) * self.ITEM_HEIGHT + 4
        self.current_h = 0.0

        calc_y = y - self.target_h if upward else y
        calc_x = min(x, WIDTH - self.MENU_WIDTH)
        calc_y = max(0, min(calc_y, HEIGHT - self.target_h))
        self.rect = pygame.Rect(calc_x, calc_y, self.MENU_WIDTH, self.target_h)

    def draw(self, surface):
        self.current_h = lerp(self.current_h, self.target_h, 0.3)
        if self.upward:
            anim_y = self.rect.bottom - self.current_h
            anim_rect = pygame.Rect(self.rect.x, anim_y, self.MENU_WIDTH, self.current_h)
        else:
            anim_rect = pygame.Rect(self.rect.x, self.rect.y, self.MENU_WIDTH, self.current_h)

        old_clip = surface.get_clip()
        surface.set_clip(anim_rect.clip(old_clip))

        pygame.draw.rect(surface, COLOR_WIN_BG, anim_rect)
        pygame.draw.line(surface, COLOR_WHITE, anim_rect.topleft, anim_rect.topright)
        pygame.draw.line(surface, COLOR_WHITE, anim_rect.topleft, anim_rect.bottomleft)
        pygame.draw.line(surface, COLOR_BLACK, anim_rect.bottomleft, anim_rect.bottomright)
        pygame.draw.line(surface, COLOR_BLACK, anim_rect.topright, anim_rect.bottomright)

        mx, my = pygame.mouse.get_pos()

        for i, item in enumerate(self.items):
            item_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2 + i * self.ITEM_HEIGHT, self.rect.w - 4,
                                    self.ITEM_HEIGHT)
            if item_rect.collidepoint(mx, my):
                if self.active_sub_index != i:
                    self.active_sub_index = i
                    if "submenu" in item and item["submenu"]:
                        sub_x = self.rect.right
                        if sub_x + self.MENU_WIDTH > WIDTH:
                            sub_x = self.rect.x - self.MENU_WIDTH
                        sub_y = item_rect.y
                        self.sub_menu = Menu(item["submenu"], sub_x, sub_y, is_root=False, upward=False)
                    else:
                        self.sub_menu = None

            is_hovered = item_rect.collidepoint(mx, my) or (self.active_sub_index == i)
            if is_hovered:
                pygame.draw.rect(surface, COLOR_HOVER, item_rect)
                txt = font.render(item["label"], True, COLOR_WHITE)
            else:
                txt = font.render(item["label"], True, COLOR_BLACK)

            surface.blit(txt, (item_rect.x + 8, item_rect.y + 4))

            if "submenu" in item and item["submenu"]:
                arrow_color = COLOR_WHITE if is_hovered else COLOR_BLACK
                arrow_txt = font_small.render("▶", True, arrow_color)
                surface.blit(arrow_txt, (item_rect.right - 14, item_rect.y + 5))

        surface.set_clip(old_clip)
        if self.sub_menu:
            self.sub_menu.draw(surface)

    def handle_event(self, event, action_handler, on_close):
        if self.sub_menu and self.sub_menu.handle_event(event, action_handler, on_close):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, item in enumerate(self.items):
                item_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2 + i * self.ITEM_HEIGHT, self.rect.w - 4,
                                        self.ITEM_HEIGHT)
                if item_rect.collidepoint(mx, my):
                    if "submenu" in item and item["submenu"]:
                        return True
                    action = item.get("action")
                    if action and action_handler:
                        action_handler(action)
                    on_close()
                    return True
            if not self.rect.collidepoint(mx, my) and self.is_root:
                on_close()
        return False


# ==========================================
# 4. 完整通用 UI 控件库
# ==========================================
class UIElement:
    def __init__(self, x=0, y=0, w=0, h=0, align="left"):
        self.rel_x = x
        self.rel_y = y
        self.base_w = w
        self.rect = pygame.Rect(x, y, w, h)
        self.id = ""
        self.align = align

    def update_layout(self, container_w, container_h):
        if self.align == "right":
            self.rect.x = container_w - self.rel_x - self.rect.w
        elif self.align == "fill":
            self.rect.x = self.rel_x
            self.rect.w = max(20, container_w - self.rel_x * 2)
        else:
            self.rect.x = self.rel_x
        self.rect.y = self.rel_y

    def draw(self, surface, abs_x, abs_y):
        pass

    def handle_event(self, event, abs_x, abs_y):
        return False


class Label(UIElement):
    def __init__(self, text, x, y, align="left"):
        super().__init__(x, y, 0, 0, align)
        self.text = text

    def draw(self, surface, abs_x, abs_y):
        txt = font.render(self.text, True, COLOR_BLACK)
        surface.blit(txt, (abs_x + self.rect.x, abs_y + self.rect.y))


class Button(UIElement):
    def __init__(self, text, x, y, w=80, h=25, callback=None, align="left"):
        super().__init__(x, y, w, h, align)
        self.text = text
        self.callback = callback
        self.is_pressed = False

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WIN_BG, r)
        if self.is_pressed:
            pygame.draw.rect(surface, COLOR_DARK, r, 1)
        else:
            pygame.draw.line(surface, COLOR_WHITE, r.topleft, r.topright)
            pygame.draw.line(surface, COLOR_WHITE, r.topleft, r.bottomleft)
            pygame.draw.line(surface, COLOR_BLACK, r.bottomleft, r.bottomright)
            pygame.draw.line(surface, COLOR_BLACK, r.topright, r.bottomright)

        txt = font.render(self.text, True, COLOR_BLACK)
        txt_rect = txt.get_rect(center=r.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and r.collidepoint(event.pos):
            self.is_pressed = True
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                if r.collidepoint(event.pos) and self.callback:
                    self.callback()
                return True
        return False


class CheckBox(UIElement):
    def __init__(self, text, x, y, checked=False, align="left"):
        super().__init__(x, y, 140, 18, align)
        self.text = text
        self.checked = checked

    def draw(self, surface, abs_x, abs_y):
        rx, ry = abs_x + self.rect.x, abs_y + self.rect.y
        box_r = pygame.Rect(rx, ry + 2, 14, 14)
        pygame.draw.rect(surface, COLOR_WHITE, box_r)
        pygame.draw.line(surface, COLOR_DARK, box_r.topleft, box_r.topright)
        pygame.draw.line(surface, COLOR_DARK, box_r.topleft, box_r.bottomleft)
        pygame.draw.line(surface, COLOR_BLACK, box_r.topright, box_r.bottomright)

        if self.checked:
            txt_v = font_small.render("✓", True, COLOR_BLACK)
            surface.blit(txt_v, (box_r.x + 2, box_r.y - 1))

        txt = font.render(self.text, True, COLOR_BLACK)
        surface.blit(txt, (rx + 20, ry))

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and r.collidepoint(event.pos):
            self.checked = not self.checked
            return True
        return False


class RadioGroup(UIElement):
    def __init__(self, options, x, y, selected_index=0, align="left"):
        super().__init__(x, y, 120, len(options) * 22, align)
        self.options = options
        self.selected_index = selected_index

    def draw(self, surface, abs_x, abs_y):
        rx, ry = abs_x + self.rect.x, abs_y + self.rect.y
        for i, opt in enumerate(self.options):
            cy = ry + i * 22 + 8
            pygame.draw.circle(surface, COLOR_WHITE, (rx + 8, cy), 6)
            pygame.draw.circle(surface, COLOR_DARK, (rx + 8, cy), 6, 1)
            if i == self.selected_index:
                pygame.draw.circle(surface, COLOR_BLACK, (rx + 8, cy), 3)
            txt = font.render(opt, True, COLOR_BLACK)
            surface.blit(txt, (rx + 20, cy - 7))

    def handle_event(self, event, abs_x, abs_y):
        rx, ry = abs_x + self.rect.x, abs_y + self.rect.y
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.options)):
                r = pygame.Rect(rx, ry + i * 22, self.rect.w, 20)
                if r.collidepoint(event.pos):
                    self.selected_index = i
                    return True
        return False


class TextBox(UIElement):
    def __init__(self, text, x, y, w=150, h=22, is_password=False, align="left"):
        super().__init__(x, y, w, h, align)
        self.text = text
        self.is_focused = False
        self.is_password = is_password

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WHITE, r)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.topright)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.bottomleft)

        disp_txt = "*" * len(self.text) if self.is_password else self.text
        txt = font.render(disp_txt + ("|" if self.is_focused else ""), True, COLOR_BLACK)
        surface.blit(txt, (r.x + 5, r.y + 3))

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_focused = r.collidepoint(event.pos)
            return self.is_focused

        if self.is_focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(event.unicode) > 0 and event.unicode.isprintable():
                self.text += event.unicode
            return True
        return False


class ProgressBar(UIElement):
    def __init__(self, x, y, w=200, h=20, progress=0.0, align="left"):
        super().__init__(x, y, w, h, align)
        self.progress = progress

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WIN_BG, r)
        pygame.draw.rect(surface, COLOR_DARK, r, 1)
        fill_w = int((self.rect.w - 4) * min(1.0, max(0.0, self.progress)))
        if fill_w > 0:
            pygame.draw.rect(surface, COLOR_PROGRESS, (r.x + 2, r.y + 2, fill_w, self.rect.h - 4))


class ComboBox(UIElement):
    def __init__(self, options, x, y, w=120, h=22, align="left"):
        super().__init__(x, y, w, h, align)
        self.options = options
        self.selected_index = 0
        self.is_open = False

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WHITE, r)
        pygame.draw.rect(surface, COLOR_BLACK, r, 1)
        txt = font.render(self.options[self.selected_index], True, COLOR_BLACK)
        surface.blit(txt, (r.x + 5, r.y + 3))

        btn_r = pygame.Rect(r.right - 18, r.y + 2, 16, r.h - 4)
        pygame.draw.rect(surface, COLOR_WIN_BG, btn_r)
        pygame.draw.rect(surface, COLOR_DARK, btn_r, 1)
        pygame.draw.polygon(surface, COLOR_BLACK,
                            [(btn_r.x + 4, btn_r.y + 6), (btn_r.x + 12, btn_r.y + 6), (btn_r.x + 8, btn_r.y + 11)])

    def draw_overlay(self, surface, abs_x, abs_y):
        if not self.is_open: return
        rx, ry = abs_x + self.rect.x, abs_y + self.rect.y
        for i, opt in enumerate(self.options):
            item_r = pygame.Rect(rx, ry + self.rect.h + i * self.rect.h, self.rect.w, self.rect.h)
            pygame.draw.rect(surface, COLOR_HOVER if i == self.selected_index else COLOR_WIN_BG, item_r)
            pygame.draw.rect(surface, COLOR_DARK, item_r, 1)
            txt = font.render(opt, True, COLOR_WHITE if i == self.selected_index else COLOR_BLACK)
            surface.blit(txt, (item_r.x + 5, item_r.y + 3))

    def handle_event(self, event, abs_x, abs_y):
        rx, ry = abs_x + self.rect.x, abs_y + self.rect.y
        r = pygame.Rect(rx, ry, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if r.collidepoint(event.pos):
                self.is_open = not self.is_open
                return True
            elif self.is_open:
                for i in range(len(self.options)):
                    item_r = pygame.Rect(rx, ry + self.rect.h + i * self.rect.h, self.rect.w, self.rect.h)
                    if item_r.collidepoint(event.pos):
                        self.selected_index = i
                        self.is_open = False
                        return True
                self.is_open = False
        return False


# ==========================================
# 5. 系统弹窗组件 (MessageBox)
# ==========================================
class MessageBox:
    @staticmethod
    def show_info(wm, title, message):
        MessageBox._dialog(wm, title, f"ℹ️ {message}", ["确定"])

    @staticmethod
    def show_warning(wm, title, message):
        MessageBox._dialog(wm, title, f"⚠️ {message}", ["确定"])

    @staticmethod
    def show_error(wm, title, message):
        MessageBox._dialog(wm, title, f"❌ {message}", ["确定"])

    @staticmethod
    def show_yes_no(wm, title, message, on_yes=None):
        def cb_yes():
            if on_yes: on_yes()

        MessageBox._dialog(wm, title, message, ["是", "否"], [cb_yes, None])

    @staticmethod
    def show_input(wm, title, prompt, on_submit=None):
        win = Window(title, WIDTH // 2 - 110, HEIGHT // 2 - 60, 220, 130)
        win.add_child(Label(prompt, 15, 10))
        tb = TextBox("", 15, 35, 190, 24, align="fill")
        win.add_child(tb)

        def submit():
            if on_submit: on_submit(tb.text)
            win.is_closed = True

        win.add_child(Button("确定", 30, 70, 70, 25, callback=submit))
        win.add_child(Button("取消", 120, 70, 70, 25, callback=lambda: setattr(win, 'is_closed', True)))
        wm.add_window(win)

    @staticmethod
    def _dialog(wm, title, msg, btns, cbs=None):
        win = Window(title, WIDTH // 2 - 120, HEIGHT // 2 - 50, 240, 100)
        win.add_child(Label(msg, 20, 15))
        for i, b_text in enumerate(btns):
            cb_func = cbs[i] if cbs and i < len(cbs) else None

            def click_handler(f=cb_func):
                if f: f()
                win.is_closed = True

            btn_x = 40 + i * 90 if len(btns) > 1 else 85
            win.add_child(Button(b_text, btn_x, 50, 65, 25, callback=click_handler))
        wm.add_window(win)


# ==========================================
# 6. 窗口容器 & 窗口管理器（平滑动画）
# ==========================================
class Window:
    MIN_WIDTH = 150
    MIN_HEIGHT = 100

    def __init__(self, title, x, y, w, h, context_menu_data=None, menu_bar_data=None):
        self.title = title
        self.rect = pygame.Rect(x, y, w, h)
        self.display_rect = pygame.Rect(x, y, w, h).copy()

        self.is_closed = False
        self.is_minimized = False
        self.is_maximized = False
        self.normal_rect = pygame.Rect(x, y, w, h)

        self.children = []
        self.context_menu_data = context_menu_data or []

        # 工具栏数据 (如未提供，自动降级为默认菜单)
        self.menu_bar_data = menu_bar_data if menu_bar_data is not None else DEFAULT_MENU_BAR
        self.active_menu = None

        self.is_dragging = False
        self.drag_offset = (0, 0)

        self.is_resizing = False
        self.resize_start_size = (w, h)
        self.resize_start_pos = (0, 0)

    def add_child(self, child: UIElement):
        self.children.append(child)
        self.update_children_layout()

    def update_children_layout(self):
        # 内部元素根据坐标偏移自适应 (顶栏 22 + 工具栏 TOOLBAR_HEIGHT)
        top_offset = 22 + (TOOLBAR_HEIGHT if self.menu_bar_data else 0)
        for child in self.children:
            child.update_layout(self.rect.w, self.rect.h - top_offset)

    @property
    def title_bar_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 22)

    @property
    def tool_bar_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y + 22, self.rect.width, TOOLBAR_HEIGHT)

    @property
    def close_btn_rect(self):
        return pygame.Rect(self.rect.right - 18, self.rect.y + 3, 15, 15)

    @property
    def max_btn_rect(self):
        return pygame.Rect(self.rect.right - 36, self.rect.y + 3, 15, 15)

    @property
    def min_btn_rect(self):
        return pygame.Rect(self.rect.right - 54, self.rect.y + 3, 15, 15)

    @property
    def resize_grip_rect(self):
        return pygame.Rect(self.rect.right - 8, self.rect.bottom - 8, 8, 8)

    def update_anim(self):
        if self.is_dragging or self.is_resizing:
            self.display_rect = pygame.Rect(self.rect)
            return

        factor = 0.25
        if self.is_minimized:
            target_x = self.rect.x
            target_y = HEIGHT - TASKBAR_HEIGHT
            target_w = self.rect.w
            target_h = 0
        else:
            target_x, target_y = self.rect.x, self.rect.y
            target_w, target_h = self.rect.w, self.rect.h

        self.display_rect.x = lerp(self.display_rect.x, target_x, factor)
        self.display_rect.y = lerp(self.display_rect.y, target_y, factor)
        self.display_rect.w = lerp(self.display_rect.w, target_w, factor)
        self.display_rect.h = lerp(self.display_rect.h, target_h, factor)

    def toggle_maximize(self):
        if self.is_maximized:
            self.rect = pygame.Rect(self.normal_rect)
            self.is_maximized = False
        else:
            self.normal_rect = pygame.Rect(self.rect)
            self.rect = pygame.Rect(0, 0, WIDTH, HEIGHT - TASKBAR_HEIGHT)
            self.is_maximized = True
        self.update_children_layout()

    def draw(self, surface, is_active):
        if self.is_closed: return

        self.update_anim()
        if self.display_rect.h < 5: return

        x, y, w, h = self.display_rect.x, self.display_rect.y, self.display_rect.w, self.display_rect.h
        win_rect = pygame.Rect(x, y, w, h)

        pygame.draw.rect(surface, COLOR_WIN_BG, win_rect)
        pygame.draw.line(surface, COLOR_WHITE, (x, y), (x + w - 1, y))
        pygame.draw.line(surface, COLOR_WHITE, (x, y), (x, y + h - 1))
        pygame.draw.line(surface, COLOR_BLACK, (x, y + h - 1), (x + w - 1, y + h - 1))
        pygame.draw.line(surface, COLOR_BLACK, (x + w - 1, y), (x + w - 1, y + h - 1))

        # 渲染标题栏
        tb_h = min(22, h)
        title_bar_rect = pygame.Rect(x, y, w, tb_h)
        t_color = COLOR_TITLE_ACTIVE if is_active else COLOR_TITLE_INACTIVE
        pygame.draw.rect(surface, t_color, title_bar_rect)

        if h > 15:
            title_txt = font.render(self.title, True, COLOR_WHITE)
            surface.blit(title_txt, (x + 5, y + 3))

            cb = pygame.Rect(x + w - 18, y + 3, 15, 15)
            mb = pygame.Rect(x + w - 36, y + 3, 15, 15)
            nb = pygame.Rect(x + w - 54, y + 3, 15, 15)

            pygame.draw.rect(surface, COLOR_WIN_BG, cb)
            pygame.draw.rect(surface, COLOR_BLACK, cb, 1)
            surface.blit(font_small.render("✕", True, COLOR_BLACK), (cb.x + 3, cb.y + 1))

            pygame.draw.rect(surface, COLOR_WIN_BG, mb)
            pygame.draw.rect(surface, COLOR_BLACK, mb, 1)
            max_icon = "❐" if self.is_maximized else "□"
            surface.blit(font_small.render(max_icon, True, COLOR_BLACK), (mb.x + 3, mb.y + 1))

            pygame.draw.rect(surface, COLOR_WIN_BG, nb)
            pygame.draw.rect(surface, COLOR_BLACK, nb, 1)
            surface.blit(font_small.render("_", True, COLOR_BLACK), (nb.x + 4, nb.y - 1))

            content_start_y = y + 22

            # 渲染顶部工具栏 (如果存在)
            if self.menu_bar_data and h > 35:
                tbar_rect = pygame.Rect(x + 2, y + 22, w - 4, TOOLBAR_HEIGHT)
                pygame.draw.rect(surface, COLOR_WIN_BG, tbar_rect)
                pygame.draw.line(surface, COLOR_DARK, (x + 2, y + 22 + TOOLBAR_HEIGHT),
                                 (x + w - 2, y + 22 + TOOLBAR_HEIGHT))

                menu_x = x + 6
                for item in self.menu_bar_data:
                    txt = font.render(item["label"], True, COLOR_BLACK)
                    tw = txt.get_width() + 12
                    item_rect = pygame.Rect(menu_x, y + 23, tw, TOOLBAR_HEIGHT - 2)

                    mx, my = pygame.mouse.get_pos()
                    if item_rect.collidepoint(mx, my):
                        pygame.draw.rect(surface, COLOR_HOVER, item_rect)
                        txt = font.render(item["label"], True, COLOR_WHITE)

                    surface.blit(txt, (menu_x + 6, y + 25))
                    menu_x += tw

                content_start_y += TOOLBAR_HEIGHT

            # 渲染窗口内容
            if h > (content_start_y - y):
                content_rect = pygame.Rect(x + 2, content_start_y, max(0, w - 4), max(0, h - (content_start_y - y) - 2))
                old_clip = surface.get_clip()
                surface.set_clip(content_rect.clip(old_clip))

                for child in self.children:
                    child.draw(surface, x, content_start_y)

                surface.set_clip(old_clip)

                for child in self.children:
                    if hasattr(child, 'draw_overlay'):
                        child.draw_overlay(surface, x, content_start_y)

                if not self.is_maximized:
                    rg = pygame.Rect(x + w - 8, y + h - 8, 8, 8)
                    pygame.draw.line(surface, COLOR_DARK, (rg.x + 6, rg.y + 1), (rg.x + 1, rg.y + 6))
                    pygame.draw.line(surface, COLOR_WHITE, (rg.x + 7, rg.y + 2), (rg.x + 2, rg.y + 7))

            # 渲染激活的下拉菜单（顶层覆盖）
            if self.active_menu:
                self.active_menu.draw(surface)

    def close_active_menu(self):
        self.active_menu = None

    def handle_event(self, event, is_top_window):
        if self.is_closed or self.is_minimized: return False

        # 优先响应弹出式工具栏菜单
        if self.active_menu:
            if self.active_menu.handle_event(event, handle_menu_action, self.close_active_menu):
                return True

        content_y = self.rect.y + 22 + (TOOLBAR_HEIGHT if self.menu_bar_data else 0)
        if is_top_window:
            for child in reversed(self.children):
                if child.handle_event(event, self.rect.x, content_y):
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.close_btn_rect.collidepoint(event.pos):
                self.is_closed = True
                return True
            if self.max_btn_rect.collidepoint(event.pos):
                self.toggle_maximize()
                return True
            if self.min_btn_rect.collidepoint(event.pos):
                self.is_minimized = True
                return True

            # 点击工具栏触发下拉多级菜单
            if self.menu_bar_data and self.tool_bar_rect.collidepoint(mx, my):
                menu_x = self.rect.x + 6
                for item in self.menu_bar_data:
                    tw = font.render(item["label"], True, COLOR_BLACK).get_width() + 12
                    item_rect = pygame.Rect(menu_x, self.rect.y + 23, tw, TOOLBAR_HEIGHT - 2)
                    if item_rect.collidepoint(mx, my):
                        if "submenu" in item:
                            self.active_menu = Menu(item["submenu"], item_rect.x, item_rect.bottom)
                        return True
                    menu_x += tw

            if not self.is_maximized and self.resize_grip_rect.collidepoint(event.pos):
                self.is_resizing = True
                self.resize_start_size = (self.rect.w, self.rect.h)
                self.resize_start_pos = event.pos
                return True

            if self.title_bar_rect.collidepoint(event.pos):
                if not self.is_maximized:
                    self.is_dragging = True
                    self.drag_offset = (self.rect.x - event.pos[0], self.rect.y - event.pos[1])
                return True

            if self.rect.collidepoint(event.pos):
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.is_dragging = False
            self.is_resizing = False

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self.rect.x = event.pos[0] + self.drag_offset[0]
                self.rect.y = event.pos[1] + self.drag_offset[1]
                return True
            elif self.is_resizing:
                dx = event.pos[0] - self.resize_start_pos[0]
                dy = event.pos[1] - self.resize_start_pos[1]
                self.rect.w = max(self.MIN_WIDTH, self.resize_start_size[0] + dx)
                self.rect.h = max(self.MIN_HEIGHT, self.resize_start_size[1] + dy)
                self.update_children_layout()
                return True

        return False


# ==========================================
# 7. 任务栏（显示自适应 Tab 及当前登录账号角色）
# ==========================================
class Taskbar:
    def __init__(self, screen_w, screen_h, start_menu_data):
        self.rect = pygame.Rect(0, screen_h - TASKBAR_HEIGHT, screen_w, TASKBAR_HEIGHT)
        self.start_btn_rect = pygame.Rect(2, screen_h - TASKBAR_HEIGHT + 2, 60, TASKBAR_HEIGHT - 4)
        self.start_menu_data = start_menu_data
        self.start_menu = None
        self.app_buttons = []

    def draw(self, surface, windows, active_window, user_name, user_role):
        pygame.draw.rect(surface, COLOR_WIN_BG, self.rect)
        pygame.draw.line(surface, COLOR_WHITE, self.rect.topleft, self.rect.topright)

        is_open = self.start_menu is not None
        pygame.draw.rect(surface, COLOR_WIN_BG, self.start_btn_rect)
        if is_open:
            pygame.draw.rect(surface, COLOR_DARK, self.start_btn_rect, 1)
        else:
            pygame.draw.line(surface, COLOR_WHITE, self.start_btn_rect.topleft, self.start_btn_rect.topright)
            pygame.draw.line(surface, COLOR_WHITE, self.start_btn_rect.topleft, self.start_btn_rect.bottomleft)
            pygame.draw.line(surface, COLOR_BLACK, self.start_btn_rect.bottomleft, self.start_btn_rect.bottomright)
            pygame.draw.line(surface, COLOR_BLACK, self.start_btn_rect.topright, self.start_btn_rect.bottomright)

        start_txt = font.render("开始", True, COLOR_BLACK)
        surface.blit(start_txt, (self.start_btn_rect.x + 16, self.start_btn_rect.y + 5))

        self.app_buttons.clear()
        start_x = self.start_btn_rect.right + 10
        btn_h = TASKBAR_HEIGHT - 6

        open_windows = [w for w in windows if not w.is_closed]
        count = len(open_windows)

        role_str = "管理员" if user_role == "admin" else "普通用户"
        user_info = font_small.render(f"[{role_str}] {user_name}", True, COLOR_BLACK)
        surface.blit(user_info, (start_x, self.rect.y + 8))

        start_x += user_info.get_width() + 15

        if count > 0:
            time_box_left = WIDTH - 75
            available_w = time_box_left - start_x - 10
            gap = 4
            max_btn_w, min_btn_w = 110, 30

            calc_w = (available_w - (count - 1) * gap) // count
            btn_w = max(min_btn_w, min(max_btn_w, calc_w))

            for win in open_windows:
                btn_rect = pygame.Rect(start_x, self.rect.y + 3, btn_w, btn_h)
                self.app_buttons.append((btn_rect, win))

                is_active = (win == active_window) and (not win.is_minimized)
                pygame.draw.rect(surface, COLOR_WIN_BG, btn_rect)
                if is_active:
                    pygame.draw.rect(surface, COLOR_DARK, btn_rect, 1)
                else:
                    pygame.draw.line(surface, COLOR_WHITE, btn_rect.topleft, btn_rect.topright)
                    pygame.draw.line(surface, COLOR_WHITE, btn_rect.topleft, btn_rect.bottomleft)
                    pygame.draw.line(surface, COLOR_BLACK, btn_rect.bottomleft, btn_rect.bottomright)
                    pygame.draw.line(surface, COLOR_BLACK, btn_rect.topright, btn_rect.bottomright)

                max_chars = max(1, (btn_w - 12) // 10)
                title_str = win.title[:max(1, max_chars - 1)] + ".." if len(win.title) > max_chars else win.title

                if btn_w >= 35:
                    txt_color = COLOR_BLACK if not is_active else COLOR_HOVER
                    txt = font_small.render(title_str, True, txt_color)
                    surface.blit(txt, (btn_rect.x + 6, btn_rect.y + 5))

                start_x += btn_w + gap

        now_str = datetime.now().strftime("%H:%M:%S")
        time_txt = font.render(now_str, True, COLOR_BLACK)
        time_box = pygame.Rect(WIDTH - 75, self.rect.y + 4, 70, TASKBAR_HEIGHT - 8)
        pygame.draw.rect(surface, COLOR_WIN_BG, time_box)
        pygame.draw.line(surface, COLOR_DARK, time_box.topleft, time_box.topright)
        pygame.draw.line(surface, COLOR_DARK, time_box.topleft, time_box.bottomleft)
        pygame.draw.line(surface, COLOR_WHITE, time_box.bottomleft, time_box.bottomright)
        surface.blit(time_txt, (time_box.x + 8, time_box.y + 4))

        if self.start_menu:
            self.start_menu.draw(surface)

    def handle_event(self, event, action_handler, wm):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_btn_rect.collidepoint(event.pos):
                if self.start_menu:
                    self.start_menu = None
                else:
                    self.start_menu = Menu(self.start_menu_data, x=2, y=self.rect.top, upward=True)
                return True

            for btn_rect, win in self.app_buttons:
                if btn_rect.collidepoint(event.pos):
                    if win.is_minimized:
                        win.is_minimized = False
                        wm.bring_to_front(win)
                    else:
                        if wm.get_top_window() == win:
                            win.is_minimized = True
                        else:
                            wm.bring_to_front(win)
                    return True

        if self.start_menu and self.start_menu.handle_event(event, action_handler, self.close_menu):
            return True

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and self.rect.collidepoint(event.pos):
            return True
        return False

    def close_menu(self):
        self.start_menu = None


# ==========================================
# 8. 应用与 JSON 依赖构建器
# ==========================================
def build_window_from_data(win_data, wm_ref=None, default_title="窗口", x_offset=0,
                           y_offset=0, bind_demo_callbacks=False):
    """从一份 JSON 窗口描述创建 Window 及其子控件。

    供 load_app_from_folder 与 build_windows_from_json 共用，
    保证两类窗口的构建逻辑完全一致。
    """
    win = Window(
        title=win_data.get("title", default_title),
        x=win_data.get("x", 100) + x_offset,
        y=win_data.get("y", 100) + y_offset,
        w=win_data.get("w", 300),
        h=win_data.get("h", 200),
        context_menu_data=win_data.get("context_menu", []),
        menu_bar_data=win_data.get("menu_bar", DEFAULT_MENU_BAR)  # 兼容未提供菜单的应用
    )

    for child_data in win_data.get("children", []):
        c_type = child_data.get("type")
        cx, cy = child_data.get("x", 0), child_data.get("y", 0)
        cid = child_data.get("id", "")
        align = child_data.get("align", "left")

        element = None
        if c_type == "label":
            element = Label(child_data.get("text", ""), cx, cy, align=align)
        elif c_type == "button":
            cb = None
            if bind_demo_callbacks:
                if cid == "btn_info":
                    cb = lambda: MessageBox.show_info(wm_ref, "信息", "这是普通信息框")
                elif cid == "btn_warn":
                    cb = lambda: MessageBox.show_warning(wm_ref, "警告", "发现警告问题！")
                elif cid == "btn_err":
                    cb = lambda: MessageBox.show_error(wm_ref, "错误", "操作触发错误❌")
                elif cid == "btn_yesno":
                    cb = lambda: MessageBox.show_yes_no(wm_ref, "确认", "是否确定执行动作？",
                                                        on_yes=lambda: print("点了Yes"))
                elif cid == "btn_input":
                    cb = lambda: MessageBox.show_input(wm_ref, "录入", "请输入您的用户名:",
                                                       on_submit=lambda txt: MessageBox.show_info(wm_ref, "结果",
                                                                                                  f"输入为: {txt}"))
            element = Button(child_data.get("text", "按钮"), cx, cy, child_data.get("w", 80),
                             child_data.get("h", 25), callback=cb, align=align)
        elif c_type == "checkbox":
            element = CheckBox(child_data.get("text", ""), cx, cy, child_data.get("checked", False), align=align)
        elif c_type == "radio":
            element = RadioGroup(child_data.get("options", []), cx, cy, child_data.get("selected_index", 0),
                                 align=align)
        elif c_type == "textbox":
            element = TextBox(child_data.get("text", ""), cx, cy, child_data.get("w", 120), child_data.get("h", 22),
                              align=align)
        elif c_type == "progressbar":
            element = ProgressBar(cx, cy, child_data.get("w", 150), child_data.get("h", 18),
                                  child_data.get("progress", 0.0), align=align)
        elif c_type == "combobox":
            element = ComboBox(child_data.get("options", []), cx, cy, child_data.get("w", 120),
                               child_data.get("h", 22), align=align)

        if element:
            element.id = cid
            win.add_child(element)

    return win


def load_app_from_folder(app_folder_name, wm_ref, x_offset=0, y_offset=0):
    app_dir = os.path.join(BASE_DIR, "apps", app_folder_name)
    ui_path = os.path.join(app_dir, "ui_config.json")
    code_path = os.path.join(app_dir, "main.py")

    if not os.path.exists(ui_path):
        print(f"配置文件缺失: {ui_path}")
        return None

    with open(ui_path, "r", encoding="utf-8") as f:
        win_data = json.load(f)

    win = build_window_from_data(win_data, wm_ref=wm_ref, default_title=app_folder_name,
                                 x_offset=x_offset, y_offset=y_offset)

    if os.path.exists(code_path):
        try:
            module_name = f"apps.{app_folder_name}.main"
            spec = importlib.util.spec_from_file_location(module_name, code_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "App"):
                win.app_instance = mod.App(win, wm_ref)
        except Exception as e:
            print(f"加载应用逻辑失败 [{app_folder_name}]: {e}")

    wm_ref.add_window(win)
    return win


class WindowManager:
    def __init__(self):
        self.windows = []

    def add_window(self, window):
        self.windows.append(window)

    def bring_to_front(self, window):
        if window in self.windows:
            self.windows.remove(window)
            self.windows.append(window)

    def get_top_window(self):
        visible_windows = [w for w in self.windows if not w.is_closed and not w.is_minimized]
        return visible_windows[-1] if visible_windows else None

    def handle_event(self, event):
        self.windows = [w for w in self.windows if not w.is_closed]
        for i in range(len(self.windows) - 1, -1, -1):
            win = self.windows[i]
            if win.handle_event(event, is_top_window=(i == len(self.windows) - 1)):
                if event.type == pygame.MOUSEBUTTONDOWN and i != len(self.windows) - 1:
                    self.bring_to_front(win)
                return True
        return False

    def draw(self, surface):
        top_win = self.get_top_window()
        for win in self.windows:
            win.draw(surface, is_active=(win == top_win))


def build_windows_from_json(win_config_path, wm_ref):
    if not os.path.exists(win_config_path):
        return []

    with open(win_config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    loaded_windows = []
    for win_data in data.get("windows", []):
        win = build_window_from_data(win_data, wm_ref=wm_ref, bind_demo_callbacks=True)
        loaded_windows.append(win)
    return loaded_windows


# ==========================================
# 9. 系统初始化与主循环
# ==========================================
wm = WindowManager()
selection_box = SelectionBox()

taskbar_cfg = {"start_menu": [], "desktop_context_menu": []}
if os.path.exists(os.path.join(BASE_DIR, "taskbar_config.json")):
    with open(os.path.join(BASE_DIR, "taskbar_config.json"), "r", encoding="utf-8") as f:
        taskbar_cfg = json.load(f)

system_operations = [
    {"label": "注销账号", "action": "sys_logout"},
    {"label": "重启系统", "action": "sys_reboot"},
    {"label": "关机系统", "action": "sys_shutdown"}
]
full_start_menu = taskbar_cfg.get("start_menu", []) + [{"label": "---", "action": ""}] + system_operations

taskbar = Taskbar(WIDTH, HEIGHT, full_start_menu)

windows = build_windows_from_json(os.path.join(BASE_DIR, "gui_config.json"), wm)
for w in windows:
    wm.add_window(w)

active_context_menu = None


def close_context_menu():
    global active_context_menu
    active_context_menu = None


def handle_menu_action(action):
    global current_state, boot_timer, active_context_menu
    close_context_menu()

    if not action:
        return

    if action.startswith("app:"):
        app_name = action.split(":")[1]
        load_app_from_folder(app_name, wm)
    elif action == "show_info":
        MessageBox.show_info(wm, "信息", "这是提示信息")
    elif action == "reset_input":
        # 清空所有已打开窗口中的文本框
        for win in wm.windows:
            for child in win.children:
                if isinstance(child, TextBox):
                    child.text = ""
    elif action == "open_test_win":
        # 打开一个新测试窗口（演示动态创建窗口）
        win = Window("新测试窗口", 150 + len(wm.windows) * 20, 120 + len(wm.windows) * 15, 280, 160)
        win.add_child(Label("这是一个动态创建的窗口", 15, 15))
        win.add_child(TextBox("", 15, 45, 200, 22))
        win.add_child(Button("确定", 15, 80, 70, 25))
        wm.add_window(win)
    elif action == "sys_info":
        MessageBox.show_info(wm, "系统信息", f"Pygame Retro System v3.0\n当前用户: {current_user}")
    elif action == "sys_logout":
        current_state = STATE_LOGIN
    elif action == "sys_reboot":
        boot_timer = 0
        current_state = STATE_BOOT
    elif action in ("sys_shutdown", "quit"):
        pygame.quit()
        sys.exit()
    elif action.startswith("menu_"):
        # 响应工具栏的各项事件操作
        MessageBox.show_info(wm, "菜单响应", f"触发了菜单动作: {action}")


login_tb_user = TextBox("admin", WIDTH // 2 - 20, HEIGHT // 2 - 40, 140, 22)
login_tb_pass = TextBox("123456", WIDTH // 2 - 20, HEIGHT // 2 - 10, 140, 22, is_password=True)
login_msg = ""
boot_timer = 0

clock = pygame.time.Clock()


def main():
    global current_state, current_user, current_role, login_msg, boot_timer, active_context_menu, clock
    init_db()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
    
            if current_state == STATE_BOOT:
                pass
    
            elif current_state == STATE_LOGIN:
                login_tb_user.handle_event(event, 0, 0)
                login_tb_pass.handle_event(event, 0, 0)
    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn_login_rect = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 30, 120, 28)
                    if btn_login_rect.collidepoint(event.pos):
                        role = verify_login(login_tb_user.text, login_tb_pass.text)
                        if role:
                            current_user = login_tb_user.text
                            current_role = role
                            current_state = STATE_DESKTOP
                            login_msg = ""
                        else:
                            login_msg = "用户名或密码错误!"
    
            elif current_state == STATE_DESKTOP:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    mx, my = event.pos
                    if my < HEIGHT - TASKBAR_HEIGHT:
                        context_items = None
                        for win in reversed(wm.windows):
                            if not win.is_minimized and win.rect.collidepoint(mx, my):
                                context_items = win.context_menu_data
                                break
                        if context_items is None:
                            context_items = taskbar_cfg.get("desktop_context_menu", [])
    
                        if context_items:
                            active_context_menu = Menu(context_items, mx, my)
                        continue
    
                if active_context_menu:
                    if active_context_menu.handle_event(event, handle_menu_action, close_context_menu):
                        continue
    
                if taskbar.handle_event(event, handle_menu_action, wm):
                    close_context_menu()
                    continue
    
                if wm.handle_event(event):
                    close_context_menu()
                    continue
    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if event.pos[1] < HEIGHT - TASKBAR_HEIGHT:
                        selection_box.start(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    selection_box.update(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    selection_box.stop()
    
        if current_state == STATE_BOOT:
            screen.fill(COLOR_BLACK)
            boot_timer += 1
            txt = font_large.render("SYSTEM STARTING...", True, COLOR_WHITE)
            screen.blit(txt, (WIDTH // 2 - 130, HEIGHT // 2 - 40))
    
            pygame.draw.rect(screen, COLOR_WHITE, (WIDTH // 2 - 150, HEIGHT // 2 + 20, 300, 12), 1)
            pygame.draw.rect(screen, COLOR_WHITE, (WIDTH // 2 - 148, HEIGHT // 2 + 22, boot_timer * 2.95, 8))
    
            if boot_timer >= 100:
                current_state = STATE_LOGIN
    
        elif current_state == STATE_LOGIN:
            screen.fill(COLOR_BG)
            box = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 80, 300, 170)
            pygame.draw.rect(screen, COLOR_WIN_BG, box)
            pygame.draw.line(screen, COLOR_WHITE, box.topleft, box.topright)
            pygame.draw.line(screen, COLOR_WHITE, box.topleft, box.bottomleft)
            pygame.draw.line(screen, COLOR_BLACK, box.bottomleft, box.bottomright)
            pygame.draw.line(screen, COLOR_BLACK, box.topright, box.bottomright)
    
            screen.blit(font.render("用户登录", True, COLOR_BLACK), (box.x + 120, box.y + 12))
            screen.blit(font.render("账号:", True, COLOR_BLACK), (box.x + 25, box.y + 42))
            screen.blit(font.render("密码:", True, COLOR_BLACK), (box.x + 25, box.y + 72))
    
            login_tb_user.draw(screen, 0, 0)
            login_tb_pass.draw(screen, 0, 0)
    
            btn_login_rect = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 35, 120, 26)
            pygame.draw.rect(screen, COLOR_WIN_BG, btn_login_rect)
            pygame.draw.line(screen, COLOR_WHITE, btn_login_rect.topleft, btn_login_rect.topright)
            pygame.draw.line(screen, COLOR_WHITE, btn_login_rect.topleft, btn_login_rect.bottomleft)
            pygame.draw.line(screen, COLOR_BLACK, btn_login_rect.bottomleft, btn_login_rect.bottomright)
            pygame.draw.line(screen, COLOR_BLACK, btn_login_rect.topright, btn_login_rect.bottomright)
            screen.blit(font.render("登 录", True, COLOR_BLACK), (btn_login_rect.x + 44, btn_login_rect.y + 4))
    
            if login_msg:
                screen.blit(font.render(login_msg, True, (200, 0, 0)), (box.x + 80, box.y + 138))
    
        elif current_state == STATE_DESKTOP:
            screen.fill(SYSTEM_CONFIG["bg_color"])
    
            wm.draw(screen)
            selection_box.draw(screen)
    
            if active_context_menu:
                active_context_menu.draw(screen)
    
            taskbar.draw(screen, wm.windows, wm.get_top_window(), current_user, current_role)
    
        pygame.display.flip()
        clock.tick(120)

if __name__ == "__main__":
    main()
