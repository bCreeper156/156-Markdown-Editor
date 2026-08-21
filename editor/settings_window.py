# -*- coding: utf-8 -*-
"""设置窗口"""
import tkinter as tk
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from .colors import get_colors
from .constants import AUTHOR, GITHUB_URL, RELEASES_URL, VERSION
from .settings_store import save_settings


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, current_theme, auto_save_enabled, auto_save_interval):
        super().__init__(master)
        self.master = master
        self.title("设置")
        self.geometry("380x380")  # 加大高度容纳关于区域
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.current_theme = current_theme
        self.auto_save_enabled = auto_save_enabled
        self.auto_save_interval = auto_save_interval

        self.colors = get_colors(current_theme)
        self.configure(fg_color=self.colors["surface"])

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # ---- 自动保存 ----
        auto_save_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        auto_save_frame.pack(fill="x", pady=5)

        self.auto_save_var = ctk.BooleanVar(value=self.auto_save_enabled)
        self.auto_save_check = ctk.CTkCheckBox(
            auto_save_frame,
            text="启用自动保存",
            variable=self.auto_save_var,
            command=self.on_auto_save_toggle,
            text_color=self.colors["text"]
        )
        self.auto_save_check.pack(side="left", padx=5)

        self.interval_label = ctk.CTkLabel(auto_save_frame, text="间隔 (秒):", text_color=self.colors["text"])
        self.interval_label.pack(side="left", padx=(10, 5))

        self.interval_entry = ctk.CTkEntry(auto_save_frame, width=60, text_color=self.colors["text"])
        self.interval_entry.insert(0, str(self.auto_save_interval))
        self.interval_entry.pack(side="left", padx=5)

        # ---- 主题 ----
        theme_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=10)

        self.theme_label = ctk.CTkLabel(theme_frame, text="主题模式:", text_color=self.colors["text"])
        self.theme_label.pack(side="left", padx=5)

        # 深色模式切换暂时禁用：仅保留浅色选项，下拉菜单置灰不可选
        self.theme_var = ctk.StringVar(value="light")
        theme_options = ["light"]
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=theme_options,
            variable=self.theme_var,
            command=self.on_theme_change,
            state="disabled",
            text_color=self.colors["text"]
        )
        self.theme_menu.pack(side="left", padx=5)

        # ---- 关于区域 ----
        about_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        about_frame.pack(fill="x", pady=15)

        ctk.CTkLabel(about_frame, text="关于", font=("Segoe UI", 14, "bold"), text_color=self.colors["text"]).pack(anchor="w")

        version_label = ctk.CTkLabel(about_frame, text=f"版本: {VERSION}", text_color=self.colors["text"])
        version_label.pack(anchor="w", pady=2)

        author_label = ctk.CTkLabel(about_frame, text=f"作者: {AUTHOR}", text_color=self.colors["text"])
        author_label.pack(anchor="w", pady=2)

        # GitHub 链接（可点击）
        github_link = ctk.CTkButton(
            about_frame,
            text="GitHub 主页",
            width=140,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            text_color=self.colors["accent"],
            hover_color=self.colors["active_line"],
            command=lambda: webbrowser.open(GITHUB_URL)
        )
        github_link.pack(anchor="w", pady=2)

        # 检查更新按钮
        update_btn = ctk.CTkButton(
            about_frame,
            text="检查更新",
            width=140,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            text_color=self.colors["text"],
            hover_color=self.colors["active_line"],
            command=lambda: webbrowser.open(RELEASES_URL)
        )
        update_btn.pack(anchor="w", pady=2)

        # 关闭按钮
        close_btn = ctk.CTkButton(main_frame, text="关闭", command=self.on_close)
        close_btn.pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_auto_save_toggle(self):
        self.master.auto_save_enabled = self.auto_save_var.get()
        if self.master.auto_save_enabled:
            self.master.reset_auto_save_timer()
        else:
            self.master.cancel_auto_save_timer()
        # 立即持久化设置
        save_settings({
            "auto_save_enabled": self.master.auto_save_enabled,
            "auto_save_interval": self.master.auto_save_interval,
        })

    def on_theme_change(self, choice):
        self.current_theme = choice
        self.master.set_theme(choice)
        self.colors = get_colors(choice)
        self.configure(fg_color=self.colors["surface"])
        # 更新当前窗口控件颜色
        self.theme_label.configure(text_color=self.colors["text"])
        self.theme_menu.configure(text_color=self.colors["text"])
        self.auto_save_check.configure(text_color=self.colors["text"])
        self.interval_label.configure(text_color=self.colors["text"])
        self.interval_entry.configure(text_color=self.colors["text"])
        # 更新关于区域的标签颜色（但按钮文字颜色可能需要单独设置）
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.configure(text_color=self.colors["text"])

    def on_close(self):
        try:
            interval = int(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
            self.master.auto_save_interval = interval
        except ValueError:
            messagebox.showwarning("无效值", "自动保存间隔必须是正整数，已恢复为默认值 30 秒。")
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, "30")
            self.master.auto_save_interval = 30

        self.master.auto_save_enabled = self.auto_save_var.get()
        if self.master.auto_save_enabled:
            self.master.reset_auto_save_timer()
        else:
            self.master.cancel_auto_save_timer()

        # 关闭设置窗口时持久化，保证下次打开设置与本次一致
        save_settings({
            "auto_save_enabled": self.master.auto_save_enabled,
            "auto_save_interval": self.master.auto_save_interval,
        })

        self.destroy()
