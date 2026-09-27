# apps/calc/main.py
from arith import evaluate as safe_evaluate


class CalcApp:
    def __init__(self, window, wm):
        self.window = window
        self.wm = wm

        # 通过 ID 获取 UI 元素引用
        self.display = self.get_element("display")

        # 绑定按钮事件
        self.bind_button("btn_1", lambda: self.append_num("1"))
        self.bind_button("btn_2", lambda: self.append_num("2"))
        self.bind_button("btn_add", lambda: self.append_num("+"))
        self.bind_button("btn_calc", self.calculate)

    def get_element(self, element_id):
        for child in self.window.children:
            if getattr(child, 'id', '') == element_id:
                return child
        return None

    def bind_button(self, element_id, callback):
        btn = self.get_element(element_id)
        if btn:
            btn.callback = callback

    def append_num(self, char):
        if self.display:
            if self.display.text == "0":
                self.display.text = char
            else:
                self.display.text += char

    def calculate(self):
        if not self.display:
            return
        try:
            self.display.text = str(safe_evaluate(self.display.text))
        except Exception:
            self.display.text = "Error"


# 系统调用的统一入口
def App(window, wm):
    return CalcApp(window, wm)