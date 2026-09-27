import pygame


class TaskListUI:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.id = ""  # 与 UIElement 子控件一致，供按 id 查找
        self.tasks = []  # tuple: (title, window_obj)
        self.selected_index = -1

    def set_tasks(self, tasks):
        self.tasks = tasks
        self.selected_index = -1

    def update_layout(self, container_w, container_h):
        self.rect.width = max(100, container_w - 20)
        self.rect.height = max(100, container_h - 40)

    def draw(self, surface, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        pygame.draw.rect(surface, (255, 255, 255), r)
        pygame.draw.rect(surface, (128, 128, 128), r, 1)

        font = pygame.font.SysFont("arial", 13)
        y_offset = r.y + 2
        for i, (title, win) in enumerate(self.tasks):
            if y_offset + 20 > r.bottom: break
            item_r = pygame.Rect(r.x + 2, y_offset, r.w - 4, 18)
            if i == self.selected_index:
                pygame.draw.rect(surface, (0, 0, 128), item_r)
                txt = font.render(title, True, (255, 255, 255))
            else:
                txt = font.render(title, True, (0, 0, 0))
            surface.blit(txt, (item_r.x + 5, item_r.y + 2))
            y_offset += 20

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and r.collidepoint(event.pos):
            idx = (event.pos[1] - r.y) // 20
            if 0 <= idx < len(self.tasks):
                self.selected_index = idx
            return True
        return False

class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm
        self.task_list = TaskListUI(10, 32, window.rect.w - 20, window.rect.h - 45)
        self.win.add_child(self.task_list)

        for child in list(self.win.children):
            if child.id == "btn_kill": child.callback = self.kill_task
            elif child.id == "btn_refresh": child.callback = self.refresh

        self.refresh()

    def refresh(self):
        tasks = []
        for w in self.wm.windows:
            if not w.is_closed:
                tasks.append((w.title, w))
        self.task_list.set_tasks(tasks)

    def kill_task(self):
        idx = self.task_list.selected_index
        if idx != -1 and idx < len(self.task_list.tasks):
            win_obj = self.task_list.tasks[idx][1]
            win_obj.is_closed = True
            self.refresh()