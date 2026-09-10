# 🖥️ Pygame Retro Desktop System

> **用 Python + Pygame 打造一个“真的像桌面操作系统”的复古 GUI 框架**
>
> 启动画面 → 用户登录 → 桌面 → 开始菜单 → 多窗口 → 菜单栏 → 右键菜单 → 控件 → 动画 → JSON 配置 → 独立 App 动态加载。
>
> 这个项目最大的特点不是“画出一个窗口”，而是尝试把 **桌面操作系统的交互模型** 搬进 Pygame，并通过 JSON 将 UI 配置与 Python 业务逻辑拆开。

---

## ✨ 项目亮点

| 能力 | 支持情况 |
|---|---|
| 🖥️ 复古桌面 UI | ✅ |
| 🔐 SQLite 用户登录 / 角色 | ✅ |
| 🚀 Boot 启动动画 | ✅ |
| 🪟 多窗口管理 | ✅ |
| 🖱️ 窗口拖拽 | ✅ |
| ↔️ 窗口缩放 | ✅ |
| ⛶ 最大化 / 最小化 / 关闭 | ✅ |
| 📋 开始菜单 | ✅ |
| 🖱️ 桌面右键菜单 | ✅ |
| 📑 多级菜单 | ✅ |
| 🧩 JSON 驱动 UI | ✅ |
| 🔌 独立 App 动态加载 | ✅ |
| 🎛️ Label / Button / CheckBox / Radio / TextBox | ✅ |
| 📊 ProgressBar / ComboBox | ✅ |
| 💬 MessageBox | ✅ |
| 📐 窗口内容自适应 | ✅ |
| 🕐 任务栏时钟 | ✅ |
| 👤 当前用户 / 角色显示 | ✅ |

项目使用固定的复古配色，例如青绿色桌面、灰色窗口、深蓝标题栏和经典的黑白立体边框，从视觉上模拟老式桌面系统。

---

# 📸 整体架构

```text
                    ┌─────────────────────────┐
                    │      Pygame 主循环       │
                    └────────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
        BOOT 启动              LOGIN 登录         DESKTOP 桌面
                                                     │
                          ┌──────────────────────────┼────────────────────┐
                          ▼                          ▼                    ▼
                    WindowManager                Taskbar              ContextMenu
                          │                          │                    │
                          ▼                          ▼                    ▼
                       Window                    Start Menu           右键菜单
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
          UIElement     MenuBar      App Instance
             │
     ┌───────┼────────┬─────────┐
     ▼       ▼        ▼         ▼
   Label   Button   TextBox   ComboBox ...
                          │
                          ▼
                    JSON 配置文件
                          │
                          ▼
                 独立 App / main.py
```

---

# 📁 推荐项目结构

代码本身会读取以下外部资源：

```text
project/
├── main.py
├── system.db
├── gui_config.json
├── taskbar_config.json
│
└── apps/
    ├── calculator/
    │   ├── ui_config.json
    │   └── main.py
    │
    ├── notepad/
    │   ├── ui_config.json
    │   └── main.py
    │
    └── demo/
        ├── ui_config.json
        └── main.py
```

其中：

- `main.py`：系统核心、窗口管理、事件循环。
- `system.db`：SQLite 用户数据库，首次运行时自动创建。
- `gui_config.json`：桌面初始窗口配置。
- `taskbar_config.json`：开始菜单和桌面右键菜单配置。
- `apps/<app_name>/ui_config.json`：App 的 UI 描述。
- `apps/<app_name>/main.py`：App 的 Python 业务逻辑。

---

# 🚀 快速开始

## 1. 安装 Python

推荐 Python 3.9+。

## 2. 安装 Pygame

```bash
pip install pygame
```

## 3. 启动

假设核心代码保存为：

```text
main.py
```

直接运行：

```bash
python main.py
```

程序启动流程：

```text
SYSTEM STARTING...
       ↓
     LOGIN
       ↓
     DESKTOP
```

---

# 🔐 默认登录账号

程序初始化 SQLite 数据库时会自动写入两个用户：

| 用户名 | 密码 | 角色 |
|---|---|---|
| `admin` | `123456` | 管理员 |
| `user` | `123456` | 普通用户 |

对应数据库逻辑：

```python
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
```

登录验证使用参数化 SQL：

```python
cursor.execute(
    "SELECT role FROM users WHERE username=? AND password=?",
    (username, password)
)
```

---

# 🧠 状态机

系统使用三个主要状态：

```python
STATE_BOOT = "BOOT"
STATE_LOGIN = "LOGIN"
STATE_DESKTOP = "DESKTOP"
```

可以理解为：

```text
BOOT
 │
 │ 启动完成
 ▼
LOGIN
 │
 │ 登录成功
 ▼
DESKTOP
```

例如注销：

```text
DESKTOP
   │
   │ sys_logout
   ▼
 LOGIN
```

重启：

```text
DESKTOP
   │
   │ sys_reboot
   ▼
 BOOT
   │
   ▼
 LOGIN
```

关机：

```text
DESKTOP
   │
   │ sys_shutdown
   ▼
 pygame.quit()
```

---

# 🪟 Window：窗口系统核心

`Window` 是整个 GUI 系统的核心容器。

它负责：

- 标题栏
- 关闭
- 最大化
- 最小化
- 拖拽
- 缩放
- 菜单栏
- 子控件
- 内容区域
- 动画
- 事件分发

创建窗口：

```python
win = Window(
    title="我的窗口",
    x=100,
    y=100,
    w=400,
    h=300
)
```

添加控件：

```python
win.add_child(
    Label("Hello Pygame!", 20, 20)
)
```

---

# 🎛️ UI 控件系统

当前内置以下控件：

```text
UIElement
├── Label
├── Button
├── CheckBox
├── RadioGroup
├── TextBox
├── ProgressBar
└── ComboBox
```

所有控件都继承自：

```python
class UIElement:
```

并拥有：

```python
draw(...)
handle_event(...)
update_layout(...)
```

这意味着你可以继续扩展：

```text
UIElement
   │
   ├── Slider
   ├── Image
   ├── ListBox
   ├── TreeView
   ├── TabView
   └── ...
```

---

# 🏷️ Label

```json
{
  "type": "label",
  "id": "title",
  "text": "欢迎使用系统",
  "x": 20,
  "y": 20
}
```

对应 Python：

```python
Label(
    text="欢迎使用系统",
    x=20,
    y=20
)
```

---

# 🔘 Button

JSON：

```json
{
  "type": "button",
  "id": "btn_info",
  "text": "系统信息",
  "x": 20,
  "y": 60,
  "w": 100,
  "h": 28
}
```

字段：

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `type` | string | 必填 | 必须是 `button` |
| `id` | string | `""` | 控件唯一标识 |
| `text` | string | `"按钮"` | 按钮文字 |
| `x` | number | `0` | X 坐标 |
| `y` | number | `0` | Y 坐标 |
| `w` | number | `80` | 宽度 |
| `h` | number | `25` | 高度 |
| `align` | string | `"left"` | 对齐方式 |

---

# ☑️ CheckBox

```json
{
  "type": "checkbox",
  "id": "remember",
  "text": "记住登录状态",
  "x": 20,
  "y": 100,
  "checked": true
}
```

支持：

```text
☐ 未选中
☑ 已选中
```

点击后：

```python
self.checked = not self.checked
```

---

# 🔘 RadioGroup

```json
{
  "type": "radio",
  "id": "theme",
  "options": [
    "经典",
    "现代",
    "高对比度"
  ],
  "selected_index": 0,
  "x": 20,
  "y": 130
}
```

其中：

```text
selected_index = 0
```

表示默认选择第一项。

---

# ⌨️ TextBox

```json
{
  "type": "textbox",
  "id": "username",
  "text": "admin",
  "x": 20,
  "y": 180,
  "w": 180,
  "h": 24
}
```

点击文本框后即可输入：

```text
admin|
```

支持：

- 鼠标聚焦
- 键盘输入
- Backspace
- 简单光标显示

---

# 🔒 密码输入

Python 原生 `TextBox` 支持：

```python
TextBox(
    "",
    20,
    20,
    180,
    24,
    is_password=True
)
```

绘制时会将内容转换成：

```text
******
```

---

# 📊 ProgressBar

```json
{
  "type": "progressbar",
  "id": "progress",
  "x": 20,
  "y": 220,
  "w": 250,
  "h": 20,
  "progress": 0.65
}
```

`progress` 范围：

```text
0.0 ─────────────── 1.0
0%                  100%
```

代码内部还会自动限制范围：

```python
min(1.0, max(0.0, self.progress))
```

所以：

```python
progress = -1
```

会被当成：

```python
0
```

而：

```python
progress = 2
```

会被当成：

```python
1
```

---

# 🔽 ComboBox

```json
{
  "type": "combobox",
  "id": "language",
  "options": [
    "中文",
    "English",
    "日本語"
  ],
  "x": 20,
  "y": 260,
  "w": 140,
  "h": 24
}
```

点击后展开：

```text
┌──────────────┐
│ 中文       ▼ │
├──────────────┤
│ 中文         │
│ English      │
│ 日本語       │
└──────────────┘
```

当前选择通过：

```python
selected_index
```

表示。

---

# 📐 align：自适应布局

控件支持：

```json
"align": "left"
```

```json
"align": "right"
```

```json
"align": "fill"
```

### left

普通左侧定位：

```text
┌──────────────────────┐
│ [Button]             │
│                      │
└──────────────────────┘
```

### right

距离右边保持相对位置：

```text
┌──────────────────────┐
│             [Button] │
└──────────────────────┘
```

### fill

自动填充：

```text
┌──────────────────────────┐
│ [      TextBox         ] │
└──────────────────────────┘
```

窗口大小发生变化时，会调用：

```python
update_children_layout()
```

重新计算控件位置和宽度。

---

# 📋 Window JSON 完整格式

一个窗口可以描述成：

```json
{
  "title": "示例窗口",
  "x": 100,
  "y": 80,
  "w": 420,
  "h": 300,

  "menu_bar": [],

  "context_menu": [],

  "children": []
}
```

字段说明：

| 字段 | 类型 | 默认值 | 作用 |
|---|---|---|---|
| `title` | string | `"窗口"` | 窗口标题 |
| `x` | number | `50` / `100` | X 坐标 |
| `y` | number | `50` / `100` | Y 坐标 |
| `w` | number | `300` | 宽度 |
| `h` | number | `200` | 高度 |
| `menu_bar` | array | 默认菜单 | 顶部菜单栏 |
| `context_menu` | array | `[]` | 窗口右键菜单 |
| `children` | array | `[]` | 子控件 |

---

# 🧩 children JSON

完整示例：

```json
{
  "title": "控件演示",
  "x": 100,
  "y": 80,
  "w": 500,
  "h": 380,

  "children": [
    {
      "type": "label",
      "id": "title",
      "text": "Pygame Retro Desktop",
      "x": 20,
      "y": 20
    },

    {
      "type": "textbox",
      "id": "username",
      "text": "admin",
      "x": 20,
      "y": 60,
      "w": 200,
      "h": 24
    },

    {
      "type": "button",
      "id": "btn_info",
      "text": "显示信息",
      "x": 20,
      "y": 100,
      "w": 100,
      "h": 28
    },

    {
      "type": "checkbox",
      "id": "remember",
      "text": "记住我",
      "x": 20,
      "y": 145,
      "checked": true
    },

    {
      "type": "radio",
      "id": "mode",
      "options": [
        "简单",
        "高级"
      ],
      "selected_index": 0,
      "x": 20,
      "y": 180
    },

    {
      "type": "progressbar",
      "id": "progress",
      "x": 20,
      "y": 240,
      "w": 250,
      "h": 20,
      "progress": 0.75
    },

    {
      "type": "combobox",
      "id": "language",
      "options": [
        "中文",
        "English"
      ],
      "x": 20,
      "y": 280,
      "w": 140,
      "h": 24
    }
  ]
}
```

---

# 🖱️ 菜单 JSON 格式

项目使用递归结构实现多级菜单。

最简单的菜单：

```json
[
  {
    "label": "打开",
    "action": "app:notepad"
  },
  {
    "label": "退出",
    "action": "quit"
  }
]
```

多级菜单：

```json
[
  {
    "label": "文件",
    "submenu": [
      {
        "label": "新建",
        "action": "menu_file_new"
      },
      {
        "label": "打开",
        "action": "menu_file_open"
      },
      {
        "label": "保存",
        "action": "menu_file_save"
      }
    ]
  },

  {
    "label": "帮助",
    "submenu": [
      {
        "label": "查看帮助",
        "action": "menu_help_view"
      },
      {
        "label": "关于",
        "action": "menu_help_about"
      }
    ]
  }
]
```

结构：

```text
文件
├── 新建
├── 打开
└── 保存

帮助
├── 查看帮助
└── 关于
```

---

# 🧭 action 是什么？

`action` 是菜单系统与业务逻辑之间的“桥”。

系统核心会根据 action 判断行为。

## 打开 App

```json
{
  "label": "计算器",
  "action": "app:calculator"
}
```

系统收到：

```text
app:calculator
```

之后：

```python
if action.startswith("app:"):
    app_name = action.split(":")[1]
    load_app_from_folder(app_name, wm)
```

于是：

```text
app:calculator
      ↓
apps/calculator/
      ↓
ui_config.json
      +
main.py
      ↓
创建窗口
```

---

# ⚙️ 系统 action

内置系统动作：

```text
sys_info
sys_logout
sys_reboot
sys_shutdown
quit
```

例如：

```json
{
  "label": "系统信息",
  "action": "sys_info"
}
```

注销：

```json
{
  "label": "注销账号",
  "action": "sys_logout"
}
```

重启：

```json
{
  "label": "重启系统",
  "action": "sys_reboot"
}
```

关机：

```json
{
  "label": "关机系统",
  "action": "sys_shutdown"
}
```

---

# 🧰 Window MenuBar

窗口顶部菜单默认是：

```text
文件    编辑    帮助
```

默认 JSON：

```json
[
  {
    "label": "文件",
    "submenu": [
      {
        "label": "新建",
        "action": "menu_file_new"
      },
      {
        "label": "打开",
        "action": "menu_file_open"
      },
      {
        "label": "保存",
        "action": "menu_file_save"
      },
      {
        "label": "退出",
        "action": "menu_file_exit"
      }
    ]
  },

  {
    "label": "编辑",
    "submenu": [
      {
        "label": "撤销",
        "action": "menu_edit_undo"
      },
      {
        "label": "剪切",
        "action": "menu_edit_cut"
      },
      {
        "label": "复制",
        "action": "menu_edit_copy"
      },
      {
        "label": "粘贴",
        "action": "menu_edit_paste"
      }
    ]
  }
]
```

如果应用没有提供 `menu_bar`，系统会自动使用默认菜单。

---

# 🖱️ 右键菜单

窗口可以拥有独立的：

```json
"context_menu"
```

例如：

```json
{
  "title": "我的窗口",

  "context_menu": [
    {
      "label": "刷新",
      "action": "menu_refresh"
    },
    {
      "label": "设置",
      "submenu": [
        {
          "label": "主题",
          "action": "menu_theme"
        },
        {
          "label": "字体",
          "action": "menu_font"
        }
      ]
    }
  ]
}
```

因此不同窗口可以拥有完全不同的右键菜单。

---

# 🧱 taskbar_config.json

任务栏配置：

```json
{
  "start_menu": [
    {
      "label": "计算器",
      "action": "app:calculator"
    },

    {
      "label": "记事本",
      "action": "app:notepad"
    },

    {
      "label": "系统信息",
      "action": "sys_info"
    }
  ],

  "desktop_context_menu": [
    {
      "label": "刷新",
      "action": "desktop_refresh"
    },

    {
      "label": "计算器",
      "action": "app:calculator"
    }
  ]
}
```

最终开始菜单大致变成：

```text
┌───────────────────┐
│ 计算器            │
│ 记事本            │
│ 系统信息          │
│ ----------------  │
│ 注销账号          │
│ 重启系统          │
│ 关机系统          │
└───────────────────┘
```

注意：系统会自动追加系统操作：

```python
system_operations = [
    {"label": "注销账号", "action": "sys_logout"},
    {"label": "重启系统", "action": "sys_reboot"},
    {"label": "关机系统", "action": "sys_shutdown"}
]
```

---

# 🧩 App 插件机制

这是项目非常值得扩展的一部分。

一个 App 不需要修改核心 GUI 系统，只需要：

```text
apps/
└── calculator/
    ├── ui_config.json
    └── main.py
```

系统会自动寻找：

```text
apps/calculator/ui_config.json
apps/calculator/main.py
```

然后通过：

```python
importlib.util.spec_from_file_location(...)
```

动态加载 Python 模块。

---

# 🔌 App main.py 规范

如果希望拥有业务逻辑，`main.py` 中定义：

```python
class App:
    def __init__(self, window, wm):
        self.window = window
        self.wm = wm
```

核心系统会自动执行：

```python
win.app_instance = mod.App(win, wm_ref)
```

因此你可以把：

```text
UI
```

与：

```text
业务逻辑
```

拆开。

---

# 🧮 完整 App 案例：Calculator

## 目录

```text
apps/
└── calculator/
    ├── ui_config.json
    └── main.py
```

## ui_config.json

```json
{
  "title": "计算器",
  "x": 180,
  "y": 120,
  "w": 320,
  "h": 240,

  "children": [
    {
      "type": "label",
      "id": "display",
      "text": "0",
      "x": 20,
      "y": 20
    },

    {
      "type": "button",
      "id": "btn_1",
      "text": "1",
      "x": 20,
      "y": 60,
      "w": 50,
      "h": 30
    },

    {
      "type": "button",
      "id": "btn_2",
      "text": "2",
      "x": 80,
      "y": 60,
      "w": 50,
      "h": 30
    },

    {
      "type": "button",
      "id": "btn_add",
      "text": "+",
      "x": 140,
      "y": 60,
      "w": 50,
      "h": 30
    }
  ]
}
```

## main.py

```python
class App:
    def __init__(self, window, wm):
        self.window = window
        self.wm = wm

        print("Calculator started")
```

> 当前核心代码中的 JSON 加载器可以创建控件，但通用 JSON Button 并不会根据任意 `id` 自动绑定业务回调；现有 `gui_config.json` 的部分示例按钮拥有硬编码的 MessageBox 行为。因此，如果要实现真正可配置的 Button → App 回调映射，建议进一步扩展事件绑定机制。

---

# 💬 MessageBox

系统内置：

```python
MessageBox.show_info(...)
MessageBox.show_warning(...)
MessageBox.show_error(...)
MessageBox.show_yes_no(...)
MessageBox.show_input(...)
```

## 信息框

```python
MessageBox.show_info(
    wm,
    "信息",
    "操作成功！"
)
```

## 警告框

```python
MessageBox.show_warning(
    wm,
    "警告",
    "发现警告问题！"
)
```

## 错误框

```python
MessageBox.show_error(
    wm,
    "错误",
    "操作失败！"
)
```

## 是 / 否

```python
MessageBox.show_yes_no(
    wm,
    "确认",
    "是否继续？",
    on_yes=lambda: print("用户选择 Yes")
)
```

## 输入框

```python
MessageBox.show_input(
    wm,
    "用户名",
    "请输入您的用户名:",
    on_submit=lambda text: print(text)
)
```

---

# 🪟 WindowManager

窗口管理器负责维护：

```python
self.windows = []
```

主要功能：

```python
add_window()
bring_to_front()
get_top_window()
handle_event()
draw()
```

窗口点击后会自动置顶：

```text
Window A
Window B
Window C  ← 点击

变成：

Window A
Window B
Window C  ← 最上层
```

这使整个系统拥有类似传统桌面系统的 Z-order 行为。

---

# 🖱️ 窗口交互

窗口支持：

### 拖动

点击标题栏：

```text
┌────────────────────────┐
│ 我的窗口               │ ← 拖动这里
├────────────────────────┤
│                        │
└────────────────────────┘
```

### 最大化

点击：

```text
□
```

窗口会变成：

```text
┌───────────────────────────────────┐
│ 我的窗口                     ❐ ✕ │
│                                   │
│                                   │
│                                   │
└───────────────────────────────────┘
```

### 最小化

点击：

```text
_
```

窗口动画移动到任务栏。

### 关闭

点击：

```text
✕
```

窗口会被标记：

```python
is_closed = True
```

WindowManager 会在事件处理中清理关闭窗口。

### 缩放

拖动右下角：

```text
┌───────────────────┐
│                   │
│                   │
│                ╲  │
└───────────────────╲
```

并限制最小尺寸：

```python
MIN_WIDTH = 150
MIN_HEIGHT = 100
```

---

# 🎞️ 平滑动画

项目没有直接瞬移窗口，而是使用简单的线性插值：

```python
def lerp(start, end, factor=0.25):
    return start + (end - start) * factor
```

窗口动画：

```python
self.display_rect.x = lerp(
    self.display_rect.x,
    target_x,
    factor
)
```

因此最小化等操作具有平滑过渡效果。

菜单同样使用动画展开：

```python
self.current_h = lerp(
    self.current_h,
    self.target_h,
    0.3
)
```

---

# 🖥️ 任务栏

任务栏高度：

```python
TASKBAR_HEIGHT = 30
```

任务栏显示：

```text
┌──────────────────────────────────────────────┐
│ 开始 │ [管理员] admin │ 窗口1 │ 窗口2 │ 12:30:01 │
└──────────────────────────────────────────────┘
```

它会自动显示：

- 开始按钮
- 当前登录用户
- 当前角色
- 已打开窗口
- 当前时间

角色显示：

```text
[管理员] admin
```

或：

```text
[普通用户] user
```

---

# ⏱️ 任务栏时间

时间由：

```python
datetime.now().strftime("%H:%M:%S")
```

生成。

例如：

```text
18:42:09
```

---

# 🌏 中文字体

代码会尝试自动查找：

### macOS

```text
/System/Library/Fonts/PingFang.ttc
/System/Library/Fonts/Hiragino Sans GB.ttc
```

### Windows

```text
C:/Windows/Fonts/simsun.ttc
C:/Windows/Fonts/msyh.ttc
```

如果没有找到，则回退到：

```python
pygame.font.SysFont("arial", size)
```

---

# 📐 分辨率

默认：

```python
WIDTH = 900
HEIGHT = 700
```

屏幕创建：

```python
screen = pygame.display.set_mode(
    (WIDTH, HEIGHT)
)
```

系统还提供：

```python
set_system_resolution(new_w, new_h)
```

用于修改分辨率，并重新调整：

- 屏幕
- 任务栏
- 开始按钮
- 窗口位置

---

# 🖱️ 桌面框选

桌面支持鼠标左键拖拽产生选择框。

核心对象：

```python
SelectionBox()
```

状态：

```text
active
start_pos
current_pos
```

拖动过程中绘制半透明区域：

```text
┌──────────────────┐
│ ░░░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░░░ │
└──────────────────┘
```

当前实现主要完成“框选视觉效果”，并未实现类似 Windows 桌面图标的实际批量选择逻辑。

---

# 🧾 JSON Schema 总览

为了方便快速查阅，可以把项目 JSON 看成以下结构：

```text
Window
│
├── title: string
├── x: number
├── y: number
├── w: number
├── h: number
│
├── menu_bar: Menu[]
├── context_menu: Menu[]
│
└── children: UIElement[]
        │
        ├── label
        ├── button
        ├── checkbox
        ├── radio
        ├── textbox
        ├── progressbar
        └── combobox
```

---

# 📚 JSON 字段速查表

## Window

```text
title        string
x            number
y            number
w            number
h            number
menu_bar     array
context_menu array
children     array
```

## Label

```text
type         "label"
id           string
text         string
x            number
y            number
align        string
```

## Button

```text
type         "button"
id           string
text         string
x            number
y            number
w            number
h            number
align        string
```

## CheckBox

```text
type         "checkbox"
id           string
text         string
x            number
y            number
checked      boolean
align        string
```

## RadioGroup

```text
type            "radio"
id              string
options         string[]
selected_index  integer
x               number
y               number
align           string
```

## TextBox

```text
type         "textbox"
id           string
text         string
x            number
y            number
w            number
h            number
align        string
```

## ProgressBar

```text
type         "progressbar"
id           string
x            number
y            number
w            number
h            number
progress     number
align        string
```

## ComboBox

```text
type         "combobox"
id           string
options      string[]
x            number
y            number
w            number
h            number
align        string
```

---

# 🧪 一个完整 GUI 配置案例

下面这个配置可以作为一个非常好的测试窗口：

```json
{
  "title": "用户设置",
  "x": 120,
  "y": 80,
  "w": 500,
  "h": 380,

  "menu_bar": [
    {
      "label": "文件",
      "submenu": [
        {
          "label": "保存",
          "action": "menu_file_save"
        },
        {
          "label": "退出",
          "action": "menu_file_exit"
        }
      ]
    },

    {
      "label": "帮助",
      "submenu": [
        {
          "label": "关于",
          "action": "menu_help_about"
        }
      ]
    }
  ],

  "context_menu": [
    {
      "label": "刷新",
      "action": "menu_refresh"
    }
  ],

  "children": [
    {
      "type": "label",
      "id": "title",
      "text": "用户设置",
      "x": 20,
      "y": 20
    },

    {
      "type": "label",
      "id": "username_label",
      "text": "用户名",
      "x": 20,
      "y": 60
    },

    {
      "type": "textbox",
      "id": "username",
      "text": "admin",
      "x": 100,
      "y": 56,
      "w": 220,
      "h": 24
    },

    {
      "type": "checkbox",
      "id": "auto_login",
      "text": "自动登录",
      "x": 20,
      "y": 100,
      "checked": true
    },

    {
      "type": "radio",
      "id": "theme",
      "options": [
        "经典主题",
        "现代主题",
        "高对比度"
      ],
      "selected_index": 0,
      "x": 20,
      "y": 140
    },

    {
      "type": "combobox",
      "id": "language",
      "options": [
        "中文",
        "English"
      ],
      "x": 20,
      "y": 220,
      "w": 150,
      "h": 24
    },

    {
      "type": "progressbar",
      "id": "loading",
      "x": 20,
      "y": 270,
      "w": 300,
      "h": 20,
      "progress": 0.8
    },

    {
      "type": "button",
      "id": "btn_info",
      "text": "确定",
      "x": 20,
      "y": 315,
      "w": 80,
      "h": 28
    }
  ]
}
```

---

# 🔄 从 JSON 到窗口的完整流程

当系统执行：

```python
build_windows_from_json("gui_config.json", wm)
```

实际上发生：

```text
gui_config.json
       │
       ▼
json.load()
       │
       ▼
读取 windows
       │
       ▼
创建 Window
       │
       ▼
读取 children
       │
       ├── type=label
       ├── type=button
       ├── type=textbox
       ├── type=checkbox
       ├── type=radio
       ├── type=progressbar
       └── type=combobox
       │
       ▼
创建 UIElement
       │
       ▼
window.add_child()
       │
       ▼
WindowManager
       │
       ▼
Pygame draw()
```

这就是整个项目最核心的 **JSON → UI → Window → Event Loop** 链路。

---

# 🏗️ 扩展自己的控件

例如增加一个 Slider：

```python
class Slider(UIElement):
    def __init__(self, x, y, w=150, value=0.5):
        super().__init__(x, y, w, 20)
        self.value = value

    def draw(self, surface, abs_x, abs_y):
        # 自定义绘制
        pass

    def handle_event(self, event, abs_x, abs_y):
        # 自定义鼠标事件
        return False
```

然后在 JSON loader 中加入：

```python
elif c_type == "slider":
    element = Slider(
        cx,
        cy,
        child_data.get("w", 150),
        child_data.get("value", 0.5)
    )
```

以后 JSON 就可以写：

```json
{
  "type": "slider",
  "id": "volume",
  "x": 20,
  "y": 300,
  "w": 200,
  "value": 0.8
}
```

这正是该架构适合继续演化的地方。

---

# 🧩 建议的事件绑定升级

当前系统的菜单已经通过：

```text
action
```

实现配置与逻辑的连接。

下一步可以让 Button 也支持：

```json
{
  "type": "button",
  "id": "save",
  "text": "保存",
  "action": "save_document"
}
```

然后统一建立：

```python
ACTION_REGISTRY = {
    "save_document": save_document,
    "open_document": open_document,
    "show_about": show_about
}
```

这样就可以进一步实现：

```text
JSON
 │
 ├── UI
 └── action
       │
       ▼
 ACTION_REGISTRY
       │
       ▼
 Python callback
```

最终可以做到真正意义上的 **声明式 GUI**。

---

# ⚠️ 当前实现的注意事项

## 1. 密码是明文

数据库目前直接保存：

```text
username
password
role
```

适合 Demo，不适合生产环境。

---

## 2. 权限角色目前主要用于显示

代码可以识别：

```text
admin
user
```

任务栏也会显示：

```text
[管理员]
[普通用户]
```

但目前没有建立完整的 RBAC 权限控制体系。

如果需要，可以扩展：

```json
{
  "action": "app:admin_panel",
  "roles": [
    "admin"
  ]
}
```

然后在执行 action 前检查当前角色。

---

## 3. Button 回调不是完全 JSON 化

部分窗口按钮的行为根据控件 `id` 在 Python 中硬编码，例如：

```text
btn_info
btn_warn
btn_err
btn_yesno
btn_input
```

因此目前是：

```text
JSON 定义 UI
+
Python 定义部分行为
```

而不是：

```text
JSON 完全定义 UI + Action
```

---

## 4. SelectionBox 当前没有图标选择模型

现在主要负责绘制：

```text
鼠标拖拽选择框
```

如果要实现完整桌面图标系统，还需要：

```text
DesktopIcon
    ↓
SelectionBox
    ↓
碰撞检测
    ↓
selected = True/False
```

---

## 5. GUI 配置必须保持合法 JSON

例如字符串必须使用双引号：

```json
{
  "title": "Hello"
}
```

而不是：

```text
{'title': 'Hello'}
```

后者是 Python 字典写法，不是标准 JSON。

---

# 🛠️ 推荐的未来路线图

如果把这个项目继续发展，可以逐渐变成一个真正的：

> **Pygame Desktop Framework**

### v3.x

当前能力：

- [x] Boot
- [x] Login
- [x] SQLite
- [x] Desktop
- [x] Window Manager
- [x] Taskbar
- [x] Menu
- [x] JSON UI
- [x] App loader

### v4.x

建议增加：

- [ ] 真正的 Button Action Registry
- [ ] 角色权限控制
- [ ] Desktop Icon
- [ ] 文件管理器
- [ ] 文件系统模拟
- [ ] Tab 控件
- [ ] ListView
- [ ] TreeView
- [ ] Slider
- [ ] Image 控件
- [ ] 键盘快捷键
- [ ] 鼠标右键菜单统一 Action
- [ ] App 生命周期

### v5.x

进一步可以加入：

```text
┌──────────────────────────────────────────┐
│              Retro Desktop OS            │
├──────────────────────────────────────────┤
│                                          │
│  📁 Files      📝 Notes      🧮 Calc      │
│                                          │
│                                          │
│                                          │
├──────────────────────────────────────────┤
│ Start │ Apps │ Settings │ User │ 12:30  │
└──────────────────────────────────────────┘
```

甚至可以设计成：

```text
Core
├── WindowManager
├── EventManager
├── ThemeManager
├── PermissionManager
├── AppManager
└── ConfigManager

UI
├── Window
├── Menu
├── Button
├── TextBox
├── ListView
└── ...

Apps
├── Calculator
├── Notepad
├── FileManager
├── Settings
└── Terminal
```

---

# 🎯 项目设计理念

这个项目真正有意思的地方在于：

```text
传统 GUI
    ↓
代码创建 UI
    ↓
代码决定布局
    ↓
代码绑定事件
```

而本项目正在向：

```text
JSON
 ↓
描述 UI
 ↓
Pygame Renderer
 ↓
Window Manager
 ↓
Event System
 ↓
App Logic
```

演进。

也就是说：

> **JSON 描述“长什么样”，Python 负责“怎么运行”。**

这让项目具备了一个轻量级 GUI Framework 的雏形。

---

# 📌 核心 API 一览

```python
# 数据库
init_db()
verify_login(username, password)

# 系统
set_system_resolution(w, h)

# 菜单
Menu(...)
handle_menu_action(action)

# UI
Label(...)
Button(...)
CheckBox(...)
RadioGroup(...)
TextBox(...)
ProgressBar(...)
ComboBox(...)

# 对话框
MessageBox.show_info(...)
MessageBox.show_warning(...)
MessageBox.show_error(...)
MessageBox.show_yes_no(...)
MessageBox.show_input(...)

# 窗口
Window(...)
Window.add_child(...)
Window.toggle_maximize(...)

# 窗口管理
WindowManager.add_window(...)
WindowManager.bring_to_front(...)
WindowManager.get_top_window(...)

# JSON
build_windows_from_json(...)
load_app_from_folder(...)
```

---

# ❤️ 总结

这是一个基于 **Python + Pygame + SQLite + JSON** 构建的轻量级复古桌面系统。

它不是简单的 Pygame 小游戏，而是已经具备了一个小型 GUI Framework 的几个关键组成部分：

```text
                  Pygame Retro Desktop
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
      System              GUI               Apps
        │                  │                  │
   ┌────┼────┐        ┌────┼────┐        ┌───┴───┐
   │    │    │        │    │    │        │       │
 SQLite Login State  Window Menu UI     JSON   Python
                                           │
                                           ▼
                                      Dynamic Load
```

如果你的目标是继续把它发展成一个真正的“Pygame 桌面操作系统模拟器”，那么最值得优先完善的是：

1. **统一 Action Registry**
2. **完整权限系统**
3. **桌面图标模型**
4. **App 生命周期管理**
5. **更多 JSON UI 控件**
6. **主题 / 配色系统**
7. **文件系统与文件管理器**
8. **快捷键和更完整的事件系统**

这样最终可以从一个 Demo 演进成一个真正具有：

> **“配置驱动 UI + 插件式 App + Window Manager + Event System”**

架构的 Pygame GUI 框架。


---

## ⭐ 如果这个项目对你有帮助

可以继续在它的基础上实现：

```text
🖥️ Desktop
├── 📁 文件管理器
├── 📝 记事本
├── 🧮 计算器
├── ⚙️ 系统设置
├── 🖥️ 终端
├── 🎨 主题管理器
└── 📦 App 商店
```

最终让 Pygame 从一个游戏开发库，变成一个属于你自己的 **Retro Desktop UI Framework**。
