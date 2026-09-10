import pygame

class CanvasUI:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.surface = pygame.Surface((w, h))
        self.surface.fill((255, 255, 255))
        self.color = (0, 0, 0)
        self.drawing = False
        self.last_pos = None

    def update_layout(self, container_w, container_h):
        self.rect.width = max(100, container_w - 20)
        self.rect.height = max(100, container_h - 40)
        old_surf = self.surface
        self.surface = pygame.Surface((self.rect.width, self.rect.height))
        self.surface.fill((255, 255, 255))
        self.surface.blit(old_surf, (0, 0))

    def draw(self, surface, abs_x, abs_y):
        pygame.draw.rect(surface, (128, 128, 128), (abs_x + self.rect.x - 1, abs_y + self.rect.y - 1, self.rect.w + 2, self.rect.h + 2), 1)
        surface.blit(self.surface, (abs_x + self.rect.x, abs_y + self.rect.y))

    def handle_event(self, event, abs_x, abs_y):
        r = pygame.Rect(abs_x + self.rect.x, abs_y + self.rect.y, self.rect.w, self.rect.h)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and r.collidepoint(event.pos):
            self.drawing = True
            self.last_pos = (event.pos[0] - r.x, event.pos[1] - r.y)
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drawing = False
            self.last_pos = None
        elif event.type == pygame.MOUSEMOTION and self.drawing:
            curr_pos = (event.pos[0] - r.x, event.pos[1] - r.y)
            if self.last_pos:
                pygame.draw.line(self.surface, self.color, self.last_pos, curr_pos, 3)
            self.last_pos = curr_pos
            return True
        return False

class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm
        self.canvas = CanvasUI(10, 32, window.rect.w - 20, window.rect.h - 45)
        self.win.add_child(self.canvas)

        # 绑定按钮颜色
        for child in list(self.win.children):
            if child.id == "btn_red": child.callback = lambda: self.set_color((255, 0, 0))
            elif child.id == "btn_green": child.callback = lambda: self.set_color((0, 200, 0))
            elif child.id == "btn_blue": child.callback = lambda: self.set_color((0, 0, 255))
            elif child.id == "btn_black": child.callback = lambda: self.set_color((0, 0, 0))
            elif child.id == "btn_clear": child.callback = self.clear_canvas

    def set_color(self, color):
        self.canvas.color = color

    def clear_canvas(self):
        self.canvas.surface.fill((255, 255, 255))