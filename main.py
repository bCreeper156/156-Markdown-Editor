# -*- coding: utf-8 -*-
"""156 Markdown Editor 入口

源码运行：python main.py
打包运行：PyInstaller 以本文件为入口（见 build.bat）
"""
import os
import sys

from editor.admin import ensure_admin
from editor.app import MarkdownEditor


def main():
    # 非管理员时自动请求 UAC 提权并以管理员身份重启本程序
    ensure_admin(script_path=os.path.abspath(__file__))

    app = MarkdownEditor()
    app.mainloop()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
