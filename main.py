import os
import re
import sys
import json
import shutil
import webbrowser
import tempfile
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import markdown
import pywinstyles

# ---------- 版本信息 ----------
VERSION = "alpha 0.1.6"
AUTHOR = "Creeper156 (bCreeper156)"
GITHUB_URL = "https://github.com/bCreeper156"
RELEASES_URL = "https://github.com/bCreeper156/156-markdown-editor/releases"

# ---------- 资源路径 ----------
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

bin_dir = resource_path("bin")
if os.path.exists(bin_dir):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

# ---------- 颜色方案 ----------
def _winui_colors(mode="light"):
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

# ---------- 设置持久化（settings.json） ----------
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings():
    """读取设置，缺失项使用默认值"""
    defaults = {"auto_save_enabled": True, "auto_save_interval": 30}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults


def save_settings(data):
    """保存设置到磁盘（覆盖写入）"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass

# ---------- 设置窗口 ----------
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

        self.colors = _winui_colors(current_theme)
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
        self.colors = _winui_colors(choice)
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


# ---------- 主编辑器 ----------
class MarkdownEditor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("156 Markdown Editor")
        self.geometry("1200x700")

        # 深色模式切换暂时禁用，启动时自动切换至 light
        ctk.set_appearance_mode("light")
        self.current_theme = "light"
        self.colors = _winui_colors(self.current_theme)

        # 读取上次保存的设置
        _settings = load_settings()
        self.auto_save_enabled = _settings.get("auto_save_enabled", True)
        self.auto_save_interval = _settings.get("auto_save_interval", 30)
        self.auto_save_timer = None

        self.update_timer = None
        self.debounce_delay = 300

        self.exporting = False

        # 应用 Mica 效果（仅 Windows，固定浅色）
        try:
            pywinstyles.apply_style(self, "light")
            pywinstyles.change_header_color(self, self.colors["bg"])
        except Exception:
            pass

        # 快捷键（菜单栏已移除，功能由工具栏按钮覆盖）
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-Shift-S>", lambda e: self.save_as_file())
        self.bind("<Alt-F4>", lambda e: self.quit_app())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-a>", lambda e: self.select_all())
        self.bind("<Control-x>", lambda e: self.cut())
        self.bind("<Control-c>", lambda e: self.copy())
        self.bind("<Control-v>", lambda e: self.paste())
        self.bind("<Delete>", lambda e: self.delete_selected())

        # ---------- 工具栏 ----------
        self.toolbar_frame = ctk.CTkFrame(self, height=40, fg_color="transparent")
        self.toolbar_frame.pack(side="top", fill="x", padx=10, pady=(5, 0))
        self.toolbar_frame.pack_propagate(False)

        file_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        file_group.pack(side="left", padx=2)
        for text, cmd in [("新建", self.new_file), ("打开", self.open_file),
                          ("保存", self.save_file), ("另存为", self.save_as_file),
                          ("关闭", self.quit_app)]:
            self._add_tool_button(file_group, text, cmd)

        ctk.CTkLabel(self.toolbar_frame, text="|", font=("Segoe UI", 14),
                     text_color=self.colors["text_secondary"]).pack(side="left", padx=5)

        edit_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        edit_group.pack(side="left", padx=2)
        for text, cmd in [("撤销", self.undo), ("重做", self.redo), ("全选", self.select_all),
                          ("剪切", self.cut), ("复制", self.copy), ("粘贴", self.paste),
                          ("删除", self.delete_selected)]:
            self._add_tool_button(edit_group, text, cmd)

        ctk.CTkLabel(self.toolbar_frame, text="|", font=("Segoe UI", 14),
                     text_color=self.colors["text_secondary"]).pack(side="left", padx=5)

        settings_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        settings_group.pack(side="left", padx=2)
        self.settings_btn = self._add_tool_button(settings_group, "设置", self.open_settings)

        # ---------- 主布局 ----------
        self.main_frame = ctk.CTkFrame(self, fg_color=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 大纲
        self.outline_frame = ctk.CTkFrame(self.main_frame, width=200, fg_color=self.colors["surface"])
        self.outline_frame.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(self.outline_frame, text="📑 大纲", font=("Segoe UI", 16),
                     text_color=self.colors["text"]).pack(pady=5)
        self.outline_listbox = tk.Listbox(
            self.outline_frame,
            bg=self.colors["surface"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            font=("Segoe UI", 11),
            relief="flat",
            highlightthickness=0
        )
        self.outline_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # 编辑区
        self.edit_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["surface"])
        self.edit_frame.pack(side="right", fill="both", expand=True)
        self.edit_frame.grid_rowconfigure(0, weight=1)
        self.edit_frame.grid_columnconfigure(0, weight=1)

        self.edit_text = ctk.CTkTextbox(
            self.edit_frame,
            wrap="word",
            font=("Segoe UI", 16),
            fg_color=self.colors["surface"],
            text_color=self.colors["text"],
            border_width=0
        )
        self.edit_text.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.text_widget = self.edit_text._textbox
        self.text_widget.config(undo=True, autoseparators=True, maxundo=50)
        self.text_widget.tag_configure("active_line", background=self.colors["active_line"])
        self.text_widget.bind("<KeyRelease>", self.on_text_change)
        self.text_widget.bind("<ButtonRelease-1>", self.highlight_active_line)
        self.text_widget.bind("<FocusIn>", self.highlight_active_line)

        self.current_file = None

        # 初始化样式标签
        self.setup_style_tags()
        self.update_outline()
        self.update_title()
        self.apply_styles()
        self.reset_auto_save_timer()

        # 点击窗口右上角 X 时也执行"提示保存"流程
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

    # ---------- 辅助方法 ----------
    def _add_tool_button(self, parent, text, command):
        btn = ctk.CTkButton(
            parent,
            text=text,
            width=60,
            height=28,
            corner_radius=4,
            fg_color="transparent",
            text_color=self.colors["text"],
            hover_color=self.colors["active_line"],
            command=command
        )
        btn.pack(side="left", padx=1)
        return btn

    # ---------- 设置窗口 ----------
    def open_settings(self):
        SettingsWindow(self, self.current_theme, self.auto_save_enabled, self.auto_save_interval)

    # ---------- 主题切换 ----------
    def set_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.current_theme = mode
        self.colors = _winui_colors(mode)

        self.main_frame.configure(fg_color=self.colors["bg"])
        self.edit_frame.configure(fg_color=self.colors["surface"])
        self.outline_frame.configure(fg_color=self.colors["surface"])
        self.outline_listbox.config(bg=self.colors["surface"], fg=self.colors["text"])
        self.edit_text.configure(fg_color=self.colors["surface"], text_color=self.colors["text"])
        self.toolbar_frame.configure(fg_color="transparent")

        self.setup_style_tags()
        self.apply_styles()

        try:
            pywinstyles.apply_style(self, "dark" if mode == "dark" else "light")
            pywinstyles.change_header_color(self, self.colors["bg"])
        except Exception:
            pass

    # ---------- 自动保存 ----------
    def reset_auto_save_timer(self):
        self.cancel_auto_save_timer()
        if self.auto_save_enabled:
            self.auto_save_timer = self.after(self.auto_save_interval * 1000, self.do_auto_save)

    def cancel_auto_save_timer(self):
        if self.auto_save_timer:
            self.after_cancel(self.auto_save_timer)
            self.auto_save_timer = None

    def do_auto_save(self):
        if self.auto_save_enabled:
            if self.edit_text.get("1.0", "end-1c").strip():
                self.save_file()
            self.reset_auto_save_timer()

    # ---------- 样式标签配置 ----------
    def setup_style_tags(self):
        style_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "bold", "italic",
                      "code", "code_block", "lang", "strike", "link", "list",
                      "quote", "hr", "task_on", "task_off", "hidden", "mark_gray"}
        for tag in style_tags:
            try:
                self.text_widget.tag_delete(tag)
            except tk.TclError:
                pass

        colors = self.colors
        self.text_widget.tag_configure("h1", font=("Segoe UI", 28, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h2", font=("Segoe UI", 25, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h3", font=("Segoe UI", 21, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h4", font=("Segoe UI", 19, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h5", font=("Segoe UI", 15, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h6", font=("Segoe UI", 14, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("bold", font=("Segoe UI", 16, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("italic", font=("Segoe UI", 16, "italic"), foreground=colors["text"])
        self.text_widget.tag_configure("code", font=("Consolas", 15),
                                       background="#3a3a3a" if self.current_theme == "dark" else "#e0e0e0",
                                       foreground="#d4d4d4" if self.current_theme == "dark" else "#000000")
        self.text_widget.tag_configure("code_block", font=("Consolas", 15),
                                       background="#3a3a3a" if self.current_theme == "dark" else "#e0e0e0",
                                       foreground="#d4d4d4" if self.current_theme == "dark" else "#000000",
                                       lmargin1=20, lmargin2=20)
        self.text_widget.tag_configure("lang", font=("Consolas", 15),
                                       foreground="#569CD6" if self.current_theme == "dark" else "#0078d4")
        self.text_widget.tag_configure("strike", overstrike=True, foreground=colors["text_secondary"])
        self.text_widget.tag_configure("link", foreground=colors["accent"], underline=True)
        self.text_widget.tag_configure("list", lmargin1=20, lmargin2=40)
        self.text_widget.tag_configure("quote", lmargin1=20, lmargin2=20,
                                       foreground=colors["text_secondary"])
        self.text_widget.tag_configure("hr", foreground=colors["text_secondary"])
        self.text_widget.tag_configure("task_on", font=("Segoe UI", 16), foreground=colors["text"])
        self.text_widget.tag_configure("task_off", font=("Segoe UI", 16), foreground=colors["text"])

        # hidden 标签（elide 隐藏标记符号）
        try:
            self.text_widget.tag_configure("hidden", elide=True)
        except tk.TclError:
            self.text_widget.tag_configure("hidden", foreground=colors["bg"])

        # 光标所在行的标记符号：露出现有样式代码并显示为灰色
        self.text_widget.tag_configure("mark_gray", foreground=colors["text_secondary"])

        self.text_widget.tag_lower("active_line")
        for i in range(1, 7):
            self.text_widget.tag_raise(f"h{i}")
        self.text_widget.tag_raise("code_block")
        self.text_widget.tag_raise("lang")
        self.text_widget.tag_raise("bold")
        self.text_widget.tag_raise("italic")
        self.text_widget.tag_raise("strike")
        self.text_widget.tag_raise("link")

    # ---------- 核心渲染 ----------
    def apply_styles(self, active_pos=None):
        """光标点在哪段文本上，只露出该段对应的 MD 标记（灰色显示）"""
        style_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "bold", "italic",
                      "code", "code_block", "lang", "strike", "link", "list",
                      "quote", "hr", "task_on", "task_off", "hidden", "mark_gray"}
        for tag in style_tags:
            self.text_widget.tag_remove(tag, "1.0", "end")

        content = self.text_widget.get("1.0", "end-1c")
        if not content.strip():
            return

        lines = content.split("\n")

        # 光标字符偏移（相对 content，0 起始）
        if active_pos is None:
            try:
                line, col = self.text_widget.index("insert").split(".")
                line, col = int(line), int(col)
                active_pos = sum(len(l) + 1 for l in lines[:line - 1]) + col
            except (tk.TclError, ValueError):
                active_pos = 0

        # 光标所在行（供块级标记使用）
        offset = 0
        active_line = 1
        for i, l in enumerate(lines):
            offset += len(l) + 1
            if active_pos < offset:
                active_line = i + 1
                break
        else:
            active_line = len(lines)

        def mark_tag(line_no):
            """块级标记：光标所在行显示灰色，其余行隐藏"""
            return "mark_gray" if line_no == active_line else "hidden"

        def span_tag(start, end):
            """行内标记：仅当光标落在该标记覆盖的字符范围内时显示灰色"""
            return "mark_gray" if start <= active_pos <= end else "hidden"

        # ---- 块级样式：正则处理（标题、引用、列表、水平线） ----
        in_code_block = False

        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"

            if re.match(r'^```', line.strip()):
                in_code_block = not in_code_block
                self.text_widget.tag_add("code_block", line_start, line_end)
                continue

            if in_code_block:
                self.text_widget.tag_add("code_block", line_start, line_end)
                if i > 0 and re.match(r'^```\w+', lines[i-1].strip()):
                    lang_match = re.search(r'```(\w+)', lines[i-1])
                    if lang_match:
                        lang = lang_match.group(1)
                        self.text_widget.tag_add("lang", line_start, line_end)
                continue

            # 标题
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                header_len = len(m.group(1)) + 1
                self.text_widget.tag_add(mark_tag(i + 1), line_start, f"{i+1}.{header_len}")
                self.text_widget.tag_add(f"h{len(m.group(1))}", f"{i+1}.{header_len}", line_end)
                self.text_widget.tag_raise(f"h{len(m.group(1))}")
                continue

            # 引用
            if re.match(r'^>\s', line):
                self.text_widget.tag_add(mark_tag(i + 1), line_start, f"{i+1}.2")
                self.text_widget.tag_add("quote", f"{i+1}.2", line_end)
                continue

            # 列表
            list_match = re.match(r'^(\s*[-*+]\s+|\s*\d+\.\s+)', line)
            if list_match:
                mark_len = len(list_match.group(0))
                self.text_widget.tag_add(mark_tag(i + 1), line_start, f"{i+1}.{mark_len}")
                self.text_widget.tag_add("list", f"{i+1}.{mark_len}", line_end)
                continue

            # 水平线
            if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line.strip()):
                self.text_widget.tag_add("hr", line_start, line_end)
                continue

        # ---- 内联样式：正则处理 ----
        # 粗体 **text**
        for m in re.finditer(r'\*\*([^\*]+?)\*\*', content):
            start, end = m.start(), m.end()
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{start}c", f"1.0+{start+2}c")
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{end-2}c", f"1.0+{end}c")
            self.text_widget.tag_add("bold", f"1.0+{start+2}c", f"1.0+{end-2}c")

        # 斜体 *text*
        for m in re.finditer(r'(?<!\*)\*([^\*]+?)\*(?!\*)', content):
            start, end = m.start(), m.end()
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{start}c", f"1.0+{start+1}c")
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{end-1}c", f"1.0+{end}c")
            self.text_widget.tag_add("italic", f"1.0+{start+1}c", f"1.0+{end-1}c")

        # 删除线 ~~text~~
        for m in re.finditer(r'~~([^~]+?)~~', content):
            start, end = m.start(), m.end()
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{start}c", f"1.0+{start+2}c")
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{end-2}c", f"1.0+{end}c")
            self.text_widget.tag_add("strike", f"1.0+{start+2}c", f"1.0+{end-2}c")

        # 行内代码 `code`
        for m in re.finditer(r'`([^`]+?)`', content):
            start, end = m.start(), m.end()
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{start}c", f"1.0+{start+1}c")
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{end-1}c", f"1.0+{end}c")
            self.text_widget.tag_add("code", f"1.0+{start+1}c", f"1.0+{end-1}c")

        # 链接 [text](url)
        for m in re.finditer(r'\[([^\]]+?)\]\(([^)]+?)\)', content):
            start, end = m.start(), m.end()
            text_start, text_end = m.start(1), m.end(1)
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{start}c", f"1.0+{text_start}c")
            self.text_widget.tag_add(span_tag(start, end), f"1.0+{text_end}c", f"1.0+{end}c")
            self.text_widget.tag_add("link", f"1.0+{text_start}c", f"1.0+{text_end}c")

        # 任务列表 - [ ] 和 - [x]
        for m in re.finditer(r'^(\s*[-*+]\s+)\[([ x])\]\s+(.*)', content, re.MULTILINE):
            start, end = m.start(), m.end()
            self.text_widget.tag_add("list", f"1.0+{start}c", f"1.0+{end}c")
            if m.group(2) == 'x':
                self.text_widget.tag_add("task_on", f"1.0+{m.start(2)}c", f"1.0+{m.end(2)}c")
            else:
                self.text_widget.tag_add("task_off", f"1.0+{m.start(2)}c", f"1.0+{m.end(2)}c")

    # ---------- 高亮当前行 ----------
    def highlight_active_line(self, event=None):
        self.text_widget.tag_remove("active_line", "1.0", "end")
        idx = self.text_widget.index("insert")
        line = idx.split(".")[0]
        self.text_widget.tag_add("active_line", f"{line}.0", f"{line}.end")
        # 光标移动后刷新：光标点所在的那段文本露出 MD 标记（灰色），其余隐藏
        self.apply_styles()

    # ---------- 防抖核心 ----------
    def on_text_change(self, event=None):
        if self.update_timer:
            self.after_cancel(self.update_timer)
        self.update_timer = self.after(self.debounce_delay, self._do_update)

    def _do_update(self):
        self.highlight_active_line()
        self.update_outline()
        self.reset_auto_save_timer()
        self.update_timer = None

    # ---------- 大纲：跳过代码块 ----------
    def update_outline(self):
        raw = self.edit_text.get("1.0", "end-1c")
        lines = raw.split("\n")
        headings = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if stripped.startswith("#"):
                level = 0
                for ch in stripped:
                    if ch == '#':
                        level += 1
                    else:
                        break
                if level > 0 and len(stripped) > level and stripped[level] == ' ':
                    text = stripped[level:].strip()
                    if text:
                        headings.append((level, text))

        self.outline_listbox.delete(0, tk.END)
        for level, text in headings:
            self.outline_listbox.insert(tk.END, "  " * (level - 1) + text)

    def update_title(self):
        if self.current_file:
            self.title(f"156 Markdown Editor - {os.path.basename(self.current_file)}")
        else:
            self.title("156 Markdown Editor")

    # ---------- 编辑操作 ----------
    def undo(self):
        try:
            self.text_widget.edit_undo()
        except tk.TclError:
            pass

    def redo(self):
        try:
            self.text_widget.edit_redo()
        except tk.TclError:
            pass

    def select_all(self):
        self.text_widget.tag_add("sel", "1.0", "end-1c")
        self.text_widget.focus()

    def cut(self):
        self.text_widget.event_generate("<<Cut>>")
        self.after_idle(self.on_text_change)

    def copy(self):
        self.text_widget.event_generate("<<Copy>>")

    def paste(self):
        self.text_widget.event_generate("<<Paste>>")
        self.after_idle(self.on_text_change)

    def delete_selected(self):
        try:
            self.text_widget.delete("sel.first", "sel.last")
        except tk.TclError:
            self.text_widget.delete("insert", "insert+1c")
        self.after_idle(self.on_text_change)

    # ---------- 文件操作 ----------
    def new_file(self):
        if self.ask_save_if_dirty():
            self.edit_text.delete("1.0", "end")
            self.current_file = None
            self.update_title()
            self.update_outline()
            self.reset_auto_save_timer()
            self.apply_styles()

    def open_file(self):
        if not self.ask_save_if_dirty():
            return
        path = filedialog.askopenfilename(
            title="打开 Markdown 文件",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")]
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.edit_text.delete("1.0", "end")
            self.edit_text.insert("1.0", content)
            self.current_file = path
            self.update_title()
            self.apply_styles()
            self.update_outline()
            self.reset_auto_save_timer()

    # ---------- 原子保存 ----------
    def save_file(self):
        if self.current_file:
            content = self.edit_text.get("1.0", "end-1c")
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(self.current_file),
                    suffix='.tmp'
                )
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                os.replace(tmp_path, self.current_file)
                return True
            except Exception as e:
                messagebox.showerror("保存失败", f"保存文件时出错：{e}")
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                return False
        else:
            return self.save_as_file()

    def save_as_file(self):
        if self.exporting:
            return False

        filetypes = [
            ("Markdown 文件", "*.md"),
            ("HTML 文件", "*.html"),
            ("PDF 文件", "*.pdf"),
            ("Word 文件", "*.docx")
        ]
        path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".md",
            filetypes=filetypes
        )
        if not path:
            return False

        ext = os.path.splitext(path)[1].lower()
        content = self.edit_text.get("1.0", "end-1c")

        if ext == ".md":
            tmp_path = None
            try:
                fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(path),
                    suffix='.tmp'
                )
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                os.replace(tmp_path, path)
                self.current_file = path
                self.update_title()
                return True
            except Exception as e:
                messagebox.showerror("保存失败", f"保存文件时出错：{e}")
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                return False

        elif ext == ".html":
            html = markdown.markdown(content, extensions=["extra", "toc"])
            html_doc = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>156 Markdown</title></head>
<body>{html}</body>
</html>"""
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html_doc)
                messagebox.showinfo("导出成功", f"HTML 已保存至：{path}")
                return True
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 HTML 时出错：{e}")
                return False

        elif ext == ".pdf":
            if not shutil.which("wkhtmltopdf"):
                messagebox.showerror(
                    "缺少依赖",
                    "wkhtmltopdf 未找到。\n\n"
                    "• Windows 用户：请确保程序已正确打包（包含 wkhtmltopdf.exe）。\n"
                    "• Linux / macOS 用户：请自行安装 wkhtmltopdf 并将其添加到 PATH。\n\n"
                    "下载地址：https://wkhtmltopdf.org/downloads.html"
                )
                return False

            html = markdown.markdown(content, extensions=["extra", "toc"])
            html_doc = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>156 Markdown</title></head>
<body>{html}</body>
</html>"""
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                    f.write(html_doc)
                    html_path = f.name
            except Exception as e:
                messagebox.showerror("错误", f"创建临时文件失败：{e}")
                return False

            self.exporting = True
            self.settings_btn.configure(text="导出中...", state="disabled")
            for child in self.toolbar_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for btn in child.winfo_children():
                        if isinstance(btn, ctk.CTkButton):
                            if btn.cget("text") in ["另存为", "导出中..."]:
                                btn.configure(state="disabled")

            def export_pdf():
                try:
                    subprocess.run(["wkhtmltopdf", html_path, path], check=True)
                    self.after(0, self._pdf_export_done, True, path)
                except Exception as e:
                    self.after(0, self._pdf_export_done, False, str(e))
                finally:
                    try:
                        os.unlink(html_path)
                    except:
                        pass

            threading.Thread(target=export_pdf, daemon=True).start()
            return True

        elif ext == ".docx":
            if not shutil.which("pandoc"):
                messagebox.showerror(
                    "缺少依赖",
                    "pandoc 未找到。\n\n"
                    "• Windows 用户：请确保程序已正确打包（包含 pandoc.exe）。\n"
                    "• Linux / macOS 用户：请自行安装 pandoc 并将其添加到 PATH。\n\n"
                    "下载地址：https://pandoc.org/installing.html"
                )
                return False

            try:
                import pypandoc
            except ImportError:
                messagebox.showerror("缺少依赖", "导出 Word 需要安装 pypandoc，请运行：pip install pypandoc")
                return False

            try:
                pypandoc.ensure_pandoc_installed()
            except Exception as e:
                messagebox.showerror("Pandoc 错误", f"无法获取 Pandoc 转换器：{e}")
                return False

            try:
                output = pypandoc.convert_text(content, "docx", format="md", extra_args=["--standalone"])
                with open(path, "wb") as f:
                    f.write(output)
                messagebox.showinfo("导出成功", f"Word 文档已保存至：{path}")
                return True
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 Word 时出错：{e}")
                return False

        else:
            messagebox.showwarning("未知格式", "不支持的文件扩展名，已按 Markdown 保存。")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    def _pdf_export_done(self, success, info):
        for child in self.toolbar_frame.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                for btn in child.winfo_children():
                    if isinstance(btn, ctk.CTkButton):
                        if btn.cget("text") in ["另存为", "导出中..."]:
                            btn.configure(text="另存为", state="normal")
        self.settings_btn.configure(text="设置", state="normal")
        self.exporting = False

        if success:
            messagebox.showinfo("导出成功", f"PDF 已保存至：{info}")
        else:
            messagebox.showerror("导出失败", f"生成 PDF 时出错：{info}")

    def quit_app(self):
        if self.ask_save_if_dirty():
            self.destroy()

    def ask_save_if_dirty(self):
        # 编辑器内有内容时才提示保存；内容为空直接退出
        if not self.edit_text.get("1.0", "end-1c").strip():
            return True
        ans = messagebox.askyesno("未保存", "当前文件未保存，是否保存？")
        if ans is True:
            # 保存成功才继续退出；取消另存为或保存失败则中止退出
            return self.save_file()
        elif ans is False:
            return True
        return False


if __name__ == "__main__":
    app = MarkdownEditor()
    app.mainloop()