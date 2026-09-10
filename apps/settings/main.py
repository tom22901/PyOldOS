import main as main_module  # 导入主模块以操作全局变量与函数
from main import MessageBox

class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm

        # 获取 UI 控件
        self.combo_color = self.get_child_by_id("combo_color")
        self.btn_apply_color = self.get_child_by_id("btn_apply_color")
        self.combo_res = self.get_child_by_id("combo_res")
        self.btn_apply_res = self.get_child_by_id("btn_apply_res")
        self.btn_about = self.get_child_by_id("btn_about")

        # 预设的颜色 RGB 字典
        self.color_map = {
            0: (0, 128, 128),   # 复古青色
            1: (0, 0, 128),     # 经典经典蓝
            2: (34, 139, 34),   # 深橄榄绿
            3: (20, 20, 20),    # 暗黑夜空
            4: (75, 0, 130)     # 优雅深紫
        }

        # 预设的分辨率
        self.res_map = {
            0: (900, 700),
            1: (1024, 768),
            2: (1280, 800),
            3: (800, 600)
        }

        # 绑定按钮回调
        if self.btn_apply_color:
            self.btn_apply_color.callback = self.apply_color
        if self.btn_apply_res:
            self.btn_apply_res.callback = self.apply_resolution
        if self.btn_about:
            self.btn_about.callback = lambda: MessageBox.show_info(self.wm, "关于", "Pygame 桌面系统\n版本: v2.5")

    def get_child_by_id(self, cid):
        for child in self.win.children:
            if getattr(child, "id", "") == cid:
                return child
        return None

    def apply_color(self):
        """更改背景颜色"""
        idx = self.combo_color.selected_index
        if idx in self.color_map:
            target_color = self.color_map[idx]
            main_module.SYSTEM_CONFIG["bg_color"] = target_color
            MessageBox.show_info(self.wm, "设置", "背景颜色更改成功！")

    def apply_resolution(self):
        """修改窗口分辨率"""
        idx = self.combo_res.selected_index
        if idx in self.res_map:
            w, h = self.res_map[idx]
            if hasattr(main_module, "set_system_resolution"):
                main_module.set_system_resolution(w, h)
                MessageBox.show_info(self.wm, "设置", f"分辨率已切换至 {w}x{h}")
            else:
                MessageBox.show_error(self.wm, "错误", "主程序未添加 set_system_resolution 方法！")