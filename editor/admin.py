# -*- coding: utf-8 -*-
"""管理员权限：非管理员时请求 UAC 提权并以管理员身份重启"""
import os
import subprocess
import sys


def ensure_admin(script_path=None):
    """强制以管理员身份运行：非管理员时请求 UAC 提权并以管理员身份重启本程序

    参数:
        script_path: 非打包（python 源码）运行时入口脚本的绝对路径，
                     用于提权后重启。打包为 exe 时无需传入。
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            try:
                if getattr(sys, "frozen", False):
                    # 打包后的 exe：直接把命令行参数传过去
                    params = subprocess.list2cmdline(sys.argv[1:])
                else:
                    # 源码运行（python main.py）：把入口脚本作为第一个参数
                    script = script_path or os.path.abspath(sys.argv[0])
                    params = subprocess.list2cmdline([script] + sys.argv[1:])
                # "runas" = 请求管理员权限；nShow=1 = 正常显示窗口
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            except Exception:
                pass
            # 无论提权是否成功，原进程一律退出，避免出现两个实例
            sys.exit(0)
    except AttributeError:
        pass
