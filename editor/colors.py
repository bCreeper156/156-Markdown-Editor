# -*- coding: utf-8 -*-
"""颜色方案（WinUI 风格浅色/深色）"""


def get_colors(mode="light"):
    if mode == "dark":
        return {
            "bg": "#1c1c1c",
            "surface": "#2a2a2a",
            "border": "#3a3a3a",
            "text": "#E0E0E0",
            "text_secondary": "#E0E0E0",
            "accent": "#0078d4",
            "accent_hover": "#1a8ad4",
            "active_line": "#2a2a2a",
        }
    else:
        return {
            "bg": "#f5f5f5",
            "surface": "#ffffff",
            "border": "#d0d0d0",
            "text": "#1a1a1a",
            "text_secondary": "#606060",
            "accent": "#0078d4",
            "accent_hover": "#106ebe",
            "active_line": "#e5e5e5",
        }
