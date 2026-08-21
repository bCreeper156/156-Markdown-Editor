# -*- coding: utf-8 -*-
"""Markdown 编辑器主应用"""
import os
import re
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import markdown
import pywinstyles

from .colors import get_colors
from .pdf_render import find_edge, render_pdf_with_edge
from .settings_store import load_settings
from .settings_window import SettingsWindow


class MarkdownEditor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("156 Markdown Editor")
        self.geometry("1200x700")

        # 深色模式切换暂时禁用，启动时自动切换至 light
        ctk.set_appearance_mode("light")
        self.current_theme = "light"
        self.colors = get_colors(self.current_theme)

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
        # 是否有未保存的修改：仅当文档被编辑过且未保存时为 True
        self.dirty = False

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
        self.colors = get_colors(mode)

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
        self.dirty = True  # 有编辑操作，标记未保存
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
            self.dirty = True  # 撤销也是内容变更
        except tk.TclError:
            pass

    def redo(self):
        try:
            self.text_widget.edit_redo()
            self.dirty = True  # 重做也是内容变更
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
            self.dirty = False
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
            self.dirty = False  # 刚打开的文件视为已保存
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
                self.dirty = False  # 保存成功，清除未保存标记
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
                self.dirty = False  # 另存为成功，清除未保存标记
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
                self.dirty = False  # 已导出，视为已保存
                return True
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 HTML 时出错：{e}")
                return False

        elif ext == ".pdf":
            if not shutil.which("wkhtmltopdf") and not find_edge():
                messagebox.showerror(
                    "缺少依赖",
                    "未找到可用的 PDF 渲染引擎。\n\n"
                    "• wkhtmltopdf 未找到，且系统中没有 Microsoft Edge。\n"
                    "• Windows 用户：请确保程序已正确打包（包含 wkhtmltopdf.exe）或安装 Edge。\n"
                    "• Linux / macOS 用户：请自行安装 wkhtmltopdf 并将其添加到 PATH。\n\n"
                    "wkhtmltopdf 下载地址：https://wkhtmltopdf.org/downloads.html"
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
                tmp_pdf = None
                try:
                    # wkhtmltopdf / Edge 在 Windows 上对非 ASCII 路径（中文、空格等）支持不佳，
                    # 先导出到临时目录的 ASCII 路径，成功后再移动到用户指定的路径
                    fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf", dir=tempfile.gettempdir())
                    os.close(fd)
                    os.unlink(tmp_pdf)

                    errors = []

                    # 1) 优先使用 wkhtmltopdf
                    wk = shutil.which("wkhtmltopdf")
                    if wk:
                        try:
                            result = subprocess.run(
                                [wk, "--enable-local-file-access", html_path, tmp_pdf],
                                capture_output=True, text=True, timeout=120
                            )
                            if (result.returncode != 0
                                    or not os.path.exists(tmp_pdf)
                                    or os.path.getsize(tmp_pdf) == 0):
                                errors.append(result.stderr.strip() or f"wkhtmltopdf 退出码 {result.returncode}")
                            else:
                                os.replace(tmp_pdf, path)
                                self.after(0, self._pdf_export_done, True, path)
                                return
                        except Exception as e:
                            errors.append(f"wkhtmltopdf: {e}")
                    else:
                        errors.append("wkhtmltopdf 未找到")

                    # 2) 回退：使用 Edge headless 渲染
                    if os.path.exists(tmp_pdf):
                        try:
                            os.unlink(tmp_pdf)
                        except:
                            pass
                    ok, err = render_pdf_with_edge(html_path, tmp_pdf)
                    if ok:
                        os.replace(tmp_pdf, path)
                        self.after(0, self._pdf_export_done, True, path)
                        return
                    errors.append(f"Edge: {err}")

                    # 3) 全部失败，给出明确原因
                    raise RuntimeError("；".join(errors))
                except Exception as e:
                    self.after(0, self._pdf_export_done, False, str(e))
                finally:
                    if tmp_pdf and os.path.exists(tmp_pdf):
                        try:
                            os.unlink(tmp_pdf)
                        except:
                            pass
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
                pypandoc.convert_text(content, "docx", format="md",
                                      outputfile=path, extra_args=["--standalone"])
                messagebox.showinfo("导出成功", f"Word 文档已保存至：{path}")
                self.dirty = False  # 已导出，视为已保存
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
            self.dirty = False  # 已导出，视为已保存
        else:
            messagebox.showerror("导出失败", f"生成 PDF 时出错：{info}")

    def quit_app(self):
        if self.ask_save_if_dirty():
            self.destroy()

    def ask_save_if_dirty(self):
        # 已保存且无后续编辑操作（或内容为空）时，不询问，直接放行
        if not self.dirty or not self.edit_text.get("1.0", "end-1c").strip():
            return True
        ans = messagebox.askyesno("未保存", "当前文件有未保存的修改，是否保存？")
        if ans is True:
            # 保存成功才继续退出；取消另存为或保存失败则中止退出
            return self.save_file()
        elif ans is False:
            return True
        return False
