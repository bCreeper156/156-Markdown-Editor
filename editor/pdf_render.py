# -*- coding: utf-8 -*-
"""PDF 渲染：优先 wkhtmltopdf，失败自动回退到 Edge headless"""
import os
import shutil
import subprocess
import tempfile
import time


def find_edge():
    """查找 Windows 自带的 Edge 可执行文件"""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def render_pdf_with_edge(html_path, tmp_pdf):
    """使用 Edge headless 渲染 PDF，返回 (success, error)"""
    edge = find_edge()
    if not edge:
        return False, "未找到 Microsoft Edge"
    profile_dir = tempfile.mkdtemp(prefix="edge_pdf_")
    try:
        args = [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile_dir}",
            f"--print-to-pdf={tmp_pdf}",
            "file:///" + html_path.replace("\\", "/"),
        ]
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
        # Edge 返回后文件可能仍在写入，轮询等待（最多 10 秒）
        for _ in range(100):
            if os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 0:
                return True, ""
            time.sleep(0.1)
        err = result.stderr.strip() or (f"Edge 退出码 {result.returncode}" if result.returncode else "Edge 未生成 PDF 文件")
        return False, err
    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
