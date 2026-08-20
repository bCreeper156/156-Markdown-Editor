import os
import re
import sys
import webbrowser
import tempfile
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import markdown
import pywinstyles
from tkhtmlview import HTMLLabel

# ---------- 资源路径（兼容打包） ----------
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
            "text": "#f0f0f0",
            "text_secondary": "#a0a0a0",
            "accent": "#0078d4",
            "accent_hover": "#1a8ad4",
            "active_line": "#3a3a3a",
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

# ---------- 设置窗口 ----------
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, current_theme, auto_save_enabled, auto_save_interval):
        super().__init__(master)
        self.master = master
        self.title("设置")
        self.geometry("400x450")
        self.resizable(False, False)

        # 主题
        self.current_theme = current_theme
        self.auto_save_enabled = auto_save_enabled
        self.auto_save_interval = auto_save_interval

        # 设置窗口颜色
        self.colors = _winui_colors(current_theme)
        self.configure(fg_color=self.colors["surface"])

        # ---------- 界面控件 ----------
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 自动保存
        auto_save_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        auto_save_frame.pack(fill="x", pady=5)

        self.auto_save_var = ctk.BooleanVar(value=self.auto_save_enabled)
        self.auto_save_check = ctk.CTkCheckBox(
            auto_save_frame,
            text="启用自动保存",
            variable=self.auto_save_var,
            command=self.on_auto_save_toggle
        )
        self.auto_save_check.pack(side="left", padx=5)

        self.interval_label = ctk.CTkLabel(auto_save_frame, text="间隔 (秒):")
        self.interval_label.pack(side="left", padx=(10, 5))

        self.interval_entry = ctk.CTkEntry(auto_save_frame, width=60)
        self.interval_entry.insert(0, str(self.auto_save_interval))
        self.interval_entry.pack(side="left", padx=5)

        # 主题切换
        theme_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(theme_frame, text="主题模式:").pack(side="left", padx=5)
        self.theme_var = ctk.StringVar(value=current_theme)
        theme_options = ["system", "light", "dark"]
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=theme_options,
            variable=self.theme_var,
            command=self.on_theme_change
        )
        self.theme_menu.pack(side="left", padx=5)

        # 关于信息
        about_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        about_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(about_frame, text="关于", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        version_label = ctk.CTkLabel(about_frame, text="版本: alpha 0.1.5", font=("Segoe UI", 12))
        version_label.pack(anchor="w", pady=2)

        author_label = ctk.CTkLabel(about_frame, text="制作者: Creeper156 (bCreeper156)", font=("Segoe UI", 12))
        author_label.pack(anchor="w", pady=2)

        github_link = ctk.CTkButton(
            about_frame,
            text="作者 GitHub 主页",
            width=150,
            command=lambda: webbrowser.open("https://github.com/bCreeper156")
        )
        github_link.pack(anchor="w", pady=5)

        update_btn = ctk.CTkButton(
            about_frame,
            text="检查更新",
            width=150,
            command=lambda: webbrowser.open("https://github.com/bCreeper156/156-markdown-editor/releases")
        )
        update_btn.pack(anchor="w", pady=5)

        # 关闭按钮
        close_btn = ctk.CTkButton(main_frame, text="关闭", command=self.destroy)
        close_btn.pack(pady=10)

        # 绑定窗口关闭事件，应用设置
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_auto_save_toggle(self):
        # 更新主程序的自动保存状态
        self.master.auto_save_enabled = self.auto_save_var.get()
        # 若启用则重置定时器
        if self.master.auto_save_enabled:
            self.master.reset_auto_save_timer()
        else:
            self.master.cancel_auto_save_timer()

    def on_theme_change(self, choice):
        self.current_theme = choice
        # 更新主程序主题
        self.master.set_theme(choice)
        # 更新本窗口颜色
        self.colors = _winui_colors(choice)
        self.configure(fg_color=self.colors["surface"])

    def on_close(self):
        # 读取间隔输入框的值
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

        # 应用自动保存状态
        self.master.auto_save_enabled = self.auto_save_var.get()
        if self.master.auto_save_enabled:
            self.master.reset_auto_save_timer()
        else:
            self.master.cancel_auto_save_timer()

        self.destroy()


# ---------- 主编辑器 ----------
class MarkdownEditor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("156 Markdown Editor")
        self.geometry("1200x700")

        # 初始主题
        self.current_theme = ctk.get_appearance_mode().lower()
        self.colors = _winui_colors(self.current_theme)

        # 自动保存设置
        self.auto_save_enabled = True
        self.auto_save_interval = 30
        self.auto_save_timer = None

        # 应用 Mica 效果 (Windows)
        try:
            pywinstyles.apply_style(self, "dark" if self.current_theme == "dark" else "light")
            pywinstyles.change_header_color(self, self.colors["bg"])
        except Exception:
            pass

        # ---------- 菜单 ----------
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="关闭", command=self.quit_app, accelerator="Alt+F4")
        self.menu_bar.add_cascade(label="文件", menu=file_menu)

        # ---------- 快捷键 ----------
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

        # 文件组
        file_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        file_group.pack(side="left", padx=2)
        for text, cmd in [("新建", self.new_file), ("打开", self.open_file),
                          ("保存", self.save_file), ("另存为", self.save_as_file),
                          ("关闭", self.quit_app)]:
            self._add_tool_button(file_group, text, cmd)

        ctk.CTkLabel(self.toolbar_frame, text="|", font=("Segoe UI", 14), text_color=self.colors["text_secondary"]).pack(side="left", padx=5)

        # 编辑组
        edit_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        edit_group.pack(side="left", padx=2)
        for text, cmd in [("撤销", self.undo), ("重做", self.redo), ("全选", self.select_all),
                          ("剪切", self.cut), ("复制", self.copy), ("粘贴", self.paste),
                          ("删除", self.delete_selected)]:
            self._add_tool_button(edit_group, text, cmd)

        ctk.CTkLabel(self.toolbar_frame, text="|", font=("Segoe UI", 14), text_color=self.colors["text_secondary"]).pack(side="left", padx=5)

        # 设置组（原主题切换改为设置按钮）
        settings_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        settings_group.pack(side="left", padx=2)
        self.settings_btn = self._add_tool_button(settings_group, "设置", self.open_settings)
        # 注意：_add_tool_button 中 command 为 self.open_settings

        # ---------- 主布局 ----------
        self.main_frame = ctk.CTkFrame(self, fg_color=self.colors["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 大纲
        self.outline_frame = ctk.CTkFrame(self.main_frame, width=200, fg_color=self.colors["surface"])
        self.outline_frame.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(self.outline_frame, text="📑 大纲", font=("Segoe UI", 16), text_color=self.colors["text"]).pack(pady=5)
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

        # 编辑 + 预览
        self.edit_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["surface"])
        self.edit_frame.pack(side="right", fill="both", expand=True)

        self.edit_frame.grid_rowconfigure(0, weight=1)
        self.edit_frame.grid_rowconfigure(1, weight=1)
        self.edit_frame.grid_columnconfigure(0, weight=1)

        # 编辑文本框 (所见即所得样式)
        self.edit_text = ctk.CTkTextbox(
            self.edit_frame,
            wrap="word",
            font=("Segoe UI", 12),
            fg_color=self.colors["surface"],
            text_color=self.colors["text"],
            border_width=0
        )
        self.edit_text.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.text_widget = self.edit_text._textbox
        self.text_widget.config(undo=True, autoseparators=True, maxundo=50)
        # 光标行高亮
        self.text_widget.tag_configure("active_line", background=self.colors["active_line"])
        self.text_widget.bind("<KeyRelease>", self.on_text_change)
        self.text_widget.bind("<ButtonRelease-1>", self.highlight_active_line)
        self.text_widget.bind("<FocusIn>", self.highlight_active_line)

        # 预览区 (备选)
        self.preview_frame = ctk.CTkFrame(self.edit_frame, fg_color=self.colors["surface"])
        self.preview_frame.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(self.preview_frame, text="👁️ 预览", font=("Segoe UI", 12), text_color=self.colors["text_secondary"]).pack(anchor="w")
        self.preview_html = HTMLLabel(
            self.preview_frame,
            background=self.colors["surface"],
            html="<p style='color: gray;'>预览区</p>",
            font=("Segoe UI", 12)
        )
        self.preview_html.pack(fill="both", expand=True)

        # ---------- 状态变量 ----------
        self.current_file = None

        # 初始化样式标签
        self.setup_style_tags()
        self.update_preview()
        self.update_outline()
        self.update_title()

        # 启动自动保存定时器
        self.reset_auto_save_timer()

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
        SettingsWindow(
            self,
            self.current_theme,
            self.auto_save_enabled,
            self.auto_save_interval
        )

    # ---------- 主题切换（供设置窗口调用） ----------
    def set_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.current_theme = mode
        self.colors = _winui_colors(mode)

        # 更新界面颜色
        self.main_frame.configure(fg_color=self.colors["bg"])
        self.edit_frame.configure(fg_color=self.colors["surface"])
        self.preview_frame.configure(fg_color=self.colors["surface"])
        self.outline_frame.configure(fg_color=self.colors["surface"])
        self.outline_listbox.config(bg=self.colors["surface"], fg=self.colors["text"])
        self.preview_html.configure(background=self.colors["surface"])
        self.edit_text.configure(fg_color=self.colors["surface"], text_color=self.colors["text"])
        self.toolbar_frame.configure(fg_color="transparent")
        self.setup_style_tags()
        self.apply_styles()

        # 标题栏
        try:
            pywinstyles.apply_style(self, "dark" if mode == "dark" else "light")
            pywinstyles.change_header_color(self, self.colors["bg"])
        except Exception:
            pass

    # ---------- 自动保存 ----------
    def reset_auto_save_timer(self):
        """重置自动保存定时器（每次输入后调用）"""
        self.cancel_auto_save_timer()
        if self.auto_save_enabled:
            self.auto_save_timer = self.after(self.auto_save_interval * 1000, self.do_auto_save)

    def cancel_auto_save_timer(self):
        if self.auto_save_timer:
            self.after_cancel(self.auto_save_timer)
            self.auto_save_timer = None

    def do_auto_save(self):
        """执行自动保存"""
        if self.auto_save_enabled:
            # 检查内容是否为空
            if self.edit_text.get("1.0", "end-1c").strip():
                self.save_file()
            # 重新设定定时器
            self.reset_auto_save_timer()

    # ---------- 标签样式 (Markdown 高亮) ----------
    def setup_style_tags(self):
        # 先删除旧标签（避免冲突）
        for tag in self.text_widget.tag_names():
            if tag not in ("sel", "active_line"):
                self.text_widget.tag_delete(tag)

        colors = self.colors
        self.text_widget.tag_configure("h1", font=("Segoe UI", 18, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h2", font=("Segoe UI", 16, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h3", font=("Segoe UI", 14, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h4", font=("Segoe UI", 12, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h5", font=("Segoe UI", 11, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("h6", font=("Segoe UI", 10, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("bold", font=("Segoe UI", 12, "bold"), foreground=colors["text"])
        self.text_widget.tag_configure("italic", font=("Segoe UI", 12, "italic"), foreground=colors["text"])
        self.text_widget.tag_configure("code", font=("Consolas", 11), background="#3a3a3a" if self.current_theme == "dark" else "#e0e0e0", foreground="#d4d4d4" if self.current_theme == "dark" else "#000000")
        self.text_widget.tag_configure("strike", overstrike=True, foreground=colors["text_secondary"])
        self.text_widget.tag_configure("link", foreground=colors["accent"], underline=True)
        self.text_widget.tag_configure("list", lmargin1=20, lmargin2=40)
        self.text_widget.tag_configure("quote", lmargin1=20, lmargin2=20, foreground=colors["text_secondary"])

    # ---------- 样式应用 (所见即所得) ----------
    def apply_styles(self):
        for tag in self.text_widget.tag_names():
            if tag not in ("sel", "active_line"):
                self.text_widget.tag_remove(tag, "1.0", "end")

        content = self.text_widget.get("1.0", "end-1c")
        lines = content.split("\n")
        pos = 1
        for line in lines:
            line_start = f"{pos}.0"
            line_end = f"{pos}.end"
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                if 1 <= level <= 6 and stripped[level] == " ":
                    tag = f"h{level}"
                    start = f"{pos}.{indent}"
                    end = f"{pos}.{indent + len(stripped) - level}"
                    self.text_widget.tag_add(tag, start, end)

            if re.match(r"^[\s]*[-*+]\s", line):
                self.text_widget.tag_add("list", line_start, line_end)

            if stripped.startswith(">"):
                self.text_widget.tag_add("quote", line_start, line_end)

            self._apply_inline_styles(pos, line)
            pos += 1

        self._apply_code_blocks()

    def _apply_inline_styles(self, line_num, text):
        for match in re.finditer(r"\*\*([^*]+)\*\*", text):
            start = f"{line_num}.{match.start()}"
            end = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("bold", start, end)

        for match in re.finditer(r"(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)", text):
            start = f"{line_num}.{match.start()}"
            end = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("italic", start, end)

        for match in re.finditer(r"~~([^~]+)~~", text):
            start = f"{line_num}.{match.start()}"
            end = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("strike", start, end)

        for match in re.finditer(r"`([^`]+)`", text):
            start = f"{line_num}.{match.start()}"
            end = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("code", start, end)

        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
            start = f"{line_num}.{match.start()}"
            end = f"{line_num}.{match.end()}"
            self.text_widget.tag_add("link", start, end)

    def _apply_code_blocks(self):
        content = self.text_widget.get("1.0", "end-1c")
        lines = content.split("\n")
        in_code = False
        start_line = None
        for i, line in enumerate(lines, start=1):
            if line.strip().startswith("```"):
                if not in_code:
                    in_code = True
                    start_line = i
                else:
                    in_code = False
                    for j in range(start_line, i):
                        self.text_widget.tag_add("code", f"{j}.0", f"{j}.end")
            elif in_code and line.strip():
                self.text_widget.tag_add("code", f"{i}.0", f"{i}.end")

    # ---------- 高亮当前行 ----------
    def highlight_active_line(self, event=None):
        self.text_widget.tag_remove("active_line", "1.0", "end")
        idx = self.text_widget.index("insert")
        line = idx.split(".")[0]
        self.text_widget.tag_add("active_line", f"{line}.0", f"{line}.end")

    # ---------- 事件绑定 ----------
    def on_text_change(self, event=None):
        self.apply_styles()
        self.update_preview()
        self.update_outline()
        self.highlight_active_line()
        # 重置自动保存定时器
        self.reset_auto_save_timer()

    def update_preview(self):
        raw = self.edit_text.get("1.0", "end-1c")
        html = markdown.markdown(raw, extensions=["extra", "toc"])
        self.preview_html.set_html(html)

    def update_outline(self):
        raw = self.edit_text.get("1.0", "end-1c")
        lines = raw.split("\n")
        headings = []
        for line in lines:
            if line.strip().startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                text = line.lstrip("#").strip()
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

    def copy(self):
        self.text_widget.event_generate("<<Copy>>")

    def paste(self):
        self.text_widget.event_generate("<<Paste>>")

    def delete_selected(self):
        try:
            self.text_widget.delete("sel.first", "sel.last")
        except tk.TclError:
            self.text_widget.delete("insert", "insert+1c")

    # ---------- 文件操作 ----------
    def new_file(self):
        if self.ask_save_if_dirty():
            self.edit_text.delete("1.0", "end")
            self.current_file = None
            self.update_title()
            self.update_preview()
            self.update_outline()
            self.reset_auto_save_timer()

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
            self.update_preview()
            self.update_outline()
            self.reset_auto_save_timer()

    def save_file(self):
        if self.current_file:
            content = self.edit_text.get("1.0", "end-1c")
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            self.save_as_file()

    def save_as_file(self):
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
            return

        ext = os.path.splitext(path)[1].lower()
        content = self.edit_text.get("1.0", "end-1c")

        if ext == ".md":
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = path
            self.update_title()

        elif ext == ".html":
            html = markdown.markdown(content, extensions=["extra", "toc"])
            html_doc = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>156 Markdown</title></head>
<body>{html}</body>
</html>"""
            with open(path, "w", encoding="utf-8") as f:
                f.write(html_doc)
            messagebox.showinfo("导出成功", f"HTML 已保存至：{path}")

        elif ext == ".pdf":
            try:
                subprocess.run(["wkhtmltopdf", "--version"], capture_output=True, check=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                messagebox.showerror("缺少依赖", "导出 PDF 需要 wkhtmltopdf，请确保已正确安装并加入 PATH")
                return

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
                pdf_path = path
                subprocess.run(["wkhtmltopdf", html_path, pdf_path], check=True)
                os.unlink(html_path)
                messagebox.showinfo("导出成功", f"PDF 已保存至：{pdf_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 PDF 时出错：{e}")

        elif ext == ".docx":
            try:
                import pypandoc
            except ImportError:
                messagebox.showerror("缺少依赖", "导出 Word 需要安装 pypandoc，请运行：pip install pypandoc")
                return
            try:
                pypandoc.ensure_pandoc_installed()
            except Exception as e:
                messagebox.showerror("Pandoc 错误", f"无法获取 Pandoc 转换器：{e}")
                return
            try:
                output = pypandoc.convert_text(content, "docx", format="md", extra_args=["--standalone"])
                with open(path, "wb") as f:
                    f.write(output)
                messagebox.showinfo("导出成功", f"Word 文档已保存至：{path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 Word 时出错：{e}")

        else:
            messagebox.showwarning("未知格式", "不支持的文件扩展名，已按 Markdown 保存。")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def quit_app(self):
        if self.ask_save_if_dirty():
            self.destroy()

    def ask_save_if_dirty(self):
        if not self.current_file and not self.edit_text.get("1.0", "end-1c").strip():
            return True
        ans = messagebox.askyesnocancel("未保存", "当前文件未保存，是否保存？")
        if ans is True:
            self.save_file()
            return True
        elif ans is False:
            return True
        else:
            return False


if __name__ == "__main__":
    app = MarkdownEditor()
    app.mainloop()
