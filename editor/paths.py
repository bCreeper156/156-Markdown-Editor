# -*- coding: utf-8 -*-
"""资源路径：统一处理源码运行与 PyInstaller 打包两种场景下的资源定位"""
import os
import sys

# 项目根目录（源码运行时即本文件所在目录的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
    """定位资源文件：打包后位于 _MEIPASS，源码运行时位于项目根目录"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = PROJECT_ROOT
    return os.path.join(base_path, relative_path)


def get_data_dir():
    """应用数据目录（settings.json 等用户数据存放处）：
    - 源码运行：项目根目录下的 data
    - 打包运行：exe 所在目录下的 data（写入 _MEIPASS 临时目录会随程序退出丢失）
    目录不存在时自动创建。
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = PROJECT_ROOT
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _inject_bin_to_path():
    """将 bin 目录注入 PATH，供 wkhtmltopdf / pandoc 等子进程使用"""
    bin_dir = resource_path("bin")
    if os.path.exists(bin_dir):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


# 导入本模块时即完成 PATH 注入，保证子进程能直接找到工具
_inject_bin_to_path()
