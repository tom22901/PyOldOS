import subprocess
import sys

class App:
    def __init__(self, window, wm):
        self.win = window
        self.wm = wm

        for child in list(self.win.children):
            if child.id == "btn_launch":
                child.callback = self.launch_qwebengine

    def launch_qwebengine(self):
        # 建立独立子进程运行基于 PyQt6 QWebEngineView 的浏览器窗口
        py_code = """
import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

app = QApplication(sys.argv)
win = QMainWindow()
win.setWindowTitle('PyQt6 WebEngine Browser')
win.resize(900, 600)

central = QWidget()
layout = QVBoxLayout(central)

url_bar = QLineEdit('https://www.bing.com')
web = QWebEngineView()
web.setUrl(QUrl('https://www.bing.com'))

def navigate():
    url = url_bar.text()
    if not url.startswith('http'):
        url = 'https://' + url
    web.setUrl(QUrl(url))

url_bar.returnPressed.connect(navigate)

layout.addWidget(url_bar)
layout.addWidget(web)
win.setCentralWidget(central)

win.show()
sys.exit(app.exec())
"""
        subprocess.Popen([sys.executable, "-c", py_code])