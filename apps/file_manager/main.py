import os
import shutil

import pygame

from main import COLOR_BLACK, COLOR_DARK, COLOR_HOVER, COLOR_WHITE, MessageBox, UIElement, font


class FileListView(UIElement):
    """文件列表自定义渲染与交互控件"""

    def __init__(self, x, y, w, h, align="fill"):
        super().__init__(x, y, w, h, align)
        self.items = []  # 文件/文件夹列表 [(name, is_dir, path)]
        self.selected_index = -1
        self.scroll_offset = 0
        self.item_height = 24
        self.on_double_click = None

    def set_items(self, items):
        self.items = items
        self.selected_index = -1
        self.scroll_offset = 0

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, COLOR_WHITE, r)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.topright)
        pygame.draw.line(surface, COLOR_DARK, r.topleft, r.bottomleft)
        pygame.draw.line(surface, COLOR_BLACK, r.bottomright, r.topright)
        pygame.draw.line(surface, COLOR_BLACK, r.bottomright, r.bottomleft)

        old_clip = surface.get_clip()
        surface.set_clip(r.clip(old_clip))

        for i in range(len(self.items)):
            item_y = r.y + i * self.item_height - self.scroll_offset
            if item_y + self.item_height < r.y or item_y > r.bottom:
                continue

            item_r = pygame.Rect(r.x + 2, item_y, self.rect.w - 4, self.item_height)
            name, is_dir, _ = self.items[i]

            if i == self.selected_index:
                pygame.draw.rect(surface, COLOR_HOVER, item_r)
                txt_color = COLOR_WHITE
            else:
                txt_color = COLOR_BLACK

            icon = "📁 " if is_dir else "📄 "
            txt_surf = font.render(icon + name, True, txt_color)
            surface.blit(txt_surf, (item_r.x + 5, item_r.y + 4))

        surface.set_clip(old_clip)

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if not r.collidepoint(pygame.mouse.get_pos()) and event.type != pygame.MOUSEBUTTONUP:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键单击/双击选择
                rel_y = event.pos[1] - r.y + self.scroll_offset
                clicked_idx = rel_y // self.item_height
                if 0 <= clicked_idx < len(self.items):
                    if self.selected_index == clicked_idx and self.on_double_click:
                        self.on_double_click(self.items[clicked_idx])
                    else:
                        self.selected_index = clicked_idx
                return True

            elif event.button == 4:  # 滚轮向上
                self.scroll_offset = max(0, self.scroll_offset - self.item_height)
                return True
            elif event.button == 5:  # 滚轮向下
                max_scroll = max(0, len(self.items) * self.item_height - self.rect.h)
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.item_height)
                return True
        return False


class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm
        self.current_path = os.path.abspath(".")

        # 查找 UI 元素句柄
        self.txt_path = self.get_child_by_id("txt_path")
        self.txt_new_name = self.get_child_by_id("txt_new_name")
        self.btn_up = self.get_child_by_id("btn_up")
        self.btn_refresh = self.get_child_by_id("btn_refresh")
        self.btn_create_file = self.get_child_by_id("btn_create_file")
        self.btn_create_dir = self.get_child_by_id("btn_create_dir")
        self.btn_delete = self.get_child_by_id("btn_delete")

        # 挂载列表组件
        self.file_list_view = FileListView(10, 70, 500, 260, align="fill")
        self.file_list_view.on_double_click = self.on_item_double_click
        self.win.add_child(self.file_list_view)

        # 绑定点击事件
        self.btn_up.callback = self.go_parent_dir
        self.btn_refresh.callback = self.refresh_list
        self.btn_create_file.callback = self.create_file
        self.btn_create_dir.callback = self.create_directory
        self.btn_delete.callback = self.delete_selected

        self.refresh_list()

    def get_child_by_id(self, cid):
        for child in self.win.children:
            if getattr(child, "id", "") == cid:
                return child
        return None

    def refresh_list(self):
        """刷新文件与目录列表"""
        if self.txt_path:
            self.txt_path.text = self.current_path

        items = []
        try:
            for entry in os.scandir(self.current_path):
                items.append((entry.name, entry.is_dir(), entry.path))
            # 排序：文件夹优先，再按名称排序
            items.sort(key=lambda x: (not x[1], x[0].lower()))
        except Exception as e:
            MessageBox.show_error(self.wm, "错误", f"无法读取目录: {e}")

        self.file_list_view.set_items(items)

    def on_item_double_click(self, item):
        name, is_dir, path = item
        if is_dir:
            self.current_path = path
            self.refresh_list()

    def go_parent_dir(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self.refresh_list()

    def create_file(self):
        name = self.txt_new_name.text.strip() if self.txt_new_name else ""
        if not name:
            MessageBox.show_warning(self.wm, "提示", "请输入有效的文件名！")
            return

        target_path = os.path.join(self.current_path, name)
        if os.path.exists(target_path):
            MessageBox.show_warning(self.wm, "警告", "已存在同名文件或文件夹！")
            return

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("")
            self.refresh_list()
        except Exception as e:
            MessageBox.show_error(self.wm, "创建失败", str(e))

    def create_directory(self):
        name = self.txt_new_name.text.strip() if self.txt_new_name else ""
        if not name:
            MessageBox.show_warning(self.wm, "提示", "请输入有效的文件夹名！")
            return

        target_path = os.path.join(self.current_path, name)
        if os.path.exists(target_path):
            MessageBox.show_warning(self.wm, "警告", "已存在同名文件或文件夹！")
            return

        try:
            os.makedirs(target_path)
            self.refresh_list()
        except Exception as e:
            MessageBox.show_error(self.wm, "创建失败", str(e))

    def delete_selected(self):
        idx = self.file_list_view.selected_index
        if idx < 0 or idx >= len(self.file_list_view.items):
            MessageBox.show_warning(self.wm, "提示", "请先在列表中选中要删除的项目！")
            return

        name, is_dir, path = self.file_list_view.items[idx]

        def do_delete():
            try:
                if is_dir:
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.refresh_list()
            except Exception as e:
                MessageBox.show_error(self.wm, "删除失败", str(e))

        MessageBox.show_yes_no(self.wm, "确认删除", f"确定要彻底删除 '{name}' 吗？", on_yes=do_delete)