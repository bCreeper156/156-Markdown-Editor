import os
import re
import shutil
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import markdown
import pywinstyles

# Word 导出使用 pypandoc（自动处理格式）
try:
    import pypandoc
    PYPANDOC_AVAILABLE = True
except ImportError:
    PYPANDOC_AVAILABLE = False


def _find_wkhtmltopdf():
    """自动定位 wkhtmltopdf 可执行文件"""
    candidates = [
        os.environ.get("WKHTMLTOPDF_PATH", ""),
        shutil.which("wkhtmltopdf"),
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def export_pdf(html_doc, output_path):
    """使用 wkhtmltopdf 将 HTML 字符串导出为 PDF"""
    exe = _find_wkhtmltopdf()
    if not exe:
        raise FileNotFoundError(
            "未找到 wkhtmltopdf，请先安装后重试：\n"
            "https://wkhtmltopdf.org/downloads.html\n"
            "（安装后如仍找不到，可设置环境变量 WKHTMLTOPDF_PATH 指向其可执行文件）"
        )
    fd, tmp_html = tempfile.mkstemp(suffix=".html", prefix="md_export_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_doc)
        subprocess.run(
            [exe, "--quiet", "--encoding", "utf-8", "--enable-local-file-access",
             tmp_html, output_path],
            check=True
        )
    finally:
        try:
            os.unlink(tmp_html)
        except OSError:
            pass


class MarkdownEditor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("156 Markdown Editor")
        self.geometry("1200x700")
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.UI_FONT = "Segoe UI"
        self._tool_buttons = []

        c = self._winui_colors()
        # WinUI 现代背景：Windows 11 Mica 材质（失败自动回退纯色）
        try:
            pywinstyles.apply_style(self, "mica")
        except Exception:
            pass
        self.configure(fg_color=c["window"])
        try:
            pywinstyles.change_header_color(self, c["title"])
        except Exception:
            pass

        # ---------- 菜单 ----------
        self.menu_bar = tk.Menu(self, font=(self.UI_FONT, 10))
        self.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0, font=(self.UI_FONT, 10))
        file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="关闭", command=self.quit_app, accelerator="Alt+F4")
        self.menu_bar.add_cascade(label="文件", menu=file_menu)

        # 快捷键
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-Shift-S>", lambda e: self.save_as_file())
        self.bind("<Alt-F4>", lambda e: self.quit_app())

        # ---------- 工具栏（WinUI 风格按钮） ----------
        self.toolbar_frame = ctk.CTkFrame(self, height=46, fg_color="transparent")
        self.toolbar_frame.pack(side="top", fill="x", padx=8, pady=(8, 0))
        self.toolbar_frame.pack_propagate(False)

        # 文件组
        file_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        file_group.pack(side="left", padx=2)
        for text, cmd in [("新建", self.new_file), ("打开", self.open_file),
                          ("保存", self.save_file), ("另存为", self.save_as_file),
                          ("关闭", self.quit_app)]:
            self._add_tool_button(file_group, text, cmd)

        self._add_separator()

        # 编辑组
        edit_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        edit_group.pack(side="left", padx=2)
        for text, cmd in [("撤销", self.undo), ("重做", self.redo), ("全选", self.select_all),
                          ("剪切", self.cut), ("复制", self.copy), ("粘贴", self.paste),
                          ("删除", self.delete_selected)]:
            self._add_tool_button(edit_group, text, cmd)

        self._add_separator()

        # 设置组
        settings_group = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        settings_group.pack(side="left", padx=2)
        self.theme_btn = self._add_tool_button(settings_group, "切换主题", self.toggle_theme, width=90)

        # ---------- 主布局（WinUI 卡片式） ----------
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # 大纲（WinUI 侧栏卡片）
        self.outline_frame = ctk.CTkFrame(self.main_frame, width=200, fg_color=c["card"],
                                          corner_radius=8)
        self.outline_frame.pack(side="left", fill="y", padx=(0, 8))
        self.outline_title = ctk.CTkLabel(
            self.outline_frame, text="📑 大纲", font=(self.UI_FONT, 14, "bold"),
            text_color=c["muted"])
        self.outline_title.pack(pady=(10, 6))
        self.outline_listbox = tk.Listbox(
            self.outline_frame,
            bg=c["card"], fg=c["text"],
            selectbackground=c["accent"], selectforeground="#ffffff",
            font=(self.UI_FONT, 11), borderwidth=0, highlightthickness=0,
            activestyle="none"
        )
        self.outline_listbox.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        # 编辑区（WinUI 内容卡片 + 所见即所得）
        self.edit_frame = ctk.CTkFrame(self.main_frame, fg_color=c["textbox"], corner_radius=8)
        self.edit_frame.pack(side="right", fill="both", expand=True)
        self.edit_frame.grid_rowconfigure(0, weight=1)
        self.edit_frame.grid_columnconfigure(0, weight=1)

        self.edit_text = ctk.CTkTextbox(
            self.edit_frame, wrap="word", font=("Consolas", 13),
            fg_color=c["textbox"], text_color=c["text"], border_width=0, corner_radius=8)
        self.edit_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.text_widget = self.edit_text._textbox
        self.text_widget.config(undo=True, autoseparators=True, maxundo=50,
                                insertbackground=c["text"], padx=14, pady=12)
        self.edit_text.bind("<KeyRelease>", self.on_text_change)
        # 光标所在行高亮
        self.text_widget.bind("<<CursorMove>>", self.update_active_line)
        self.text_widget.bind("<ButtonRelease-1>", self.update_active_line)
        self.text_widget.bind("<FocusIn>", self.update_active_line)

        # 状态
        self.current_file = None
        self.setup_style_tags()
        self.apply_markdown_styles()
        self.update_active_line()
        self.update_outline()
        self.update_title()

    # ---------- WinUI 工具 ----------
    @staticmethod
    def _winui_colors():
        """返回当前主题的 WinUI 风格配色（Fluent 设计语言）"""
        dark = ctk.get_appearance_mode().lower() == "dark"
        if dark:
            return {
                "window": "#202020", "card": "#2b2b2b", "control": "#2b2b2b",
                "hover": "#3c3c3c", "active": "#484848", "border": "#3a3a3a",
                "text": "#ffffff", "muted": "#9e9e9e", "accent": "#60cdff",
                "textbox": "#1f1f1f", "title": "#202020",
            }
        return {
            "window": "#f3f3f3", "card": "#f9f9f9", "control": "#ffffff",
            "hover": "#e6e6e6", "active": "#cccccc", "border": "#e0e0e0",
            "text": "#1b1b1b", "muted": "#616161", "accent": "#0067c0",
            "textbox": "#ffffff", "title": "#f3f3f3",
        }

    def _add_tool_button(self, parent, text, command, width=70):
        """WinUI 风格按钮：无边框圆角、中性底色、悬停高亮"""
        c = self._winui_colors()
        btn = ctk.CTkButton(
            parent, text=text, width=width, height=30, command=command,
            font=(self.UI_FONT, 12),
            fg_color=c["control"], hover_color=c["hover"], text_color=c["text"],
            corner_radius=6, border_width=0)
        btn.pack(side="left", padx=2)
        self._tool_buttons.append(btn)
        return btn

    def _add_separator(self):
        c = self._winui_colors()
        sep = ctk.CTkFrame(self.toolbar_frame, width=1, height=24, fg_color=c["border"])
        sep.pack(side="left", padx=8)

    # ---------- 编辑方法 ----------
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
        self.edit_text.tag_add("sel", "1.0", "end-1c")
        self.edit_text.focus()

    def cut(self):
        self.edit_text.event_generate("<<Cut>>")

    def copy(self):
        self.edit_text.event_generate("<<Copy>>")

    def paste(self):
        self.edit_text.event_generate("<<Paste>>")

    def delete_selected(self):
        try:
            self.edit_text.delete("sel.first", "sel.last")
        except tk.TclError:
            self.edit_text.delete("insert", "insert+1c")

    # ---------- 主题切换 ----------
    def toggle_theme(self):
        modes = ["system", "light", "dark"]
        current = ctk.get_appearance_mode().lower()
        idx = modes.index(current) if current in modes else 0
        next_mode = modes[(idx + 1) % len(modes)]
        ctk.set_appearance_mode(next_mode)
        c = self._winui_colors()
        # 窗口与标题栏
        self.configure(fg_color=c["window"])
        try:
            pywinstyles.change_header_color(self, c["title"])
        except Exception:
            pass
        # 大纲
        self.outline_listbox.config(bg=c["card"], fg=c["text"],
                                    selectbackground=c["accent"])
        self.outline_title.configure(text_color=c["muted"])
        # 编辑区
        self.edit_frame.configure(fg_color=c["textbox"])
        self.edit_text.configure(fg_color=c["textbox"], text_color=c["text"])
        self.text_widget.config(insertbackground=c["text"])
        # 工具栏按钮
        for btn in self._tool_buttons:
            btn.configure(fg_color=c["control"], hover_color=c["hover"],
                          text_color=c["text"])
        # 重新配置并应用渲染样式
        self.setup_style_tags()
        self.apply_markdown_styles()
        self.update_active_line()

    # ---------- Markdown 渲染（编辑区即预览区，风格参考 Typedown/Muya + GitHub） ----------
    def setup_style_tags(self):
        """配置所见即所得的样式标签（随主题更新）"""
        dark = ctk.get_appearance_mode().lower() == "dark"
        t = self.text_widget
        self._style_tags = [
            "h1", "h2", "h3", "h4", "h5", "h6",
            "bold", "italic", "strikethrough", "code", "code_block", "lang",
            "blockquote", "hr", "list", "link", "img", "checkbox", "checkbox_on", "para",
        ]
        # WinUI + GitHub markdown 配色
        fg = "#ffffff" if dark else "#1b1b1b"
        muted = "#8b949e" if dark else "#57606a"
        link = "#60cdff" if dark else "#0067c0"
        hr_color = "#3d444d" if dark else "#d0d7de"
        code_bg = "#2b2b2b" if dark else "#f0f0f0"
        quote_bg = "#2b2b2b" if dark else "#f5f5f5"
        check_bg = "#3c3c3c" if dark else "#eaeef2"
        check_on = "#3fb950" if dark else "#1a7f37"
        active_bg = "#2a2a2a" if dark else "#f0f0f0"

        # 标题：GitHub 比例（2em/1.5em/1.25em…），h1/h2 带底部边框（下划线模拟）
        sizes = {1: 24, 2: 20, 3: 17, 4: 15, 5: 14, 6: 13}
        for level, size in sizes.items():
            kwargs = dict(
                font=("Microsoft YaHei UI", size, "bold"),
                foreground=fg, spacing1=10, spacing3=6,
            )
            if level <= 2:
                kwargs["underline"] = True
            t.tag_configure(f"h{level}", **kwargs)
        t.tag_configure("bold", font=("Consolas", 13, "bold"), foreground=fg)
        t.tag_configure("italic", font=("Consolas", 13, "italic"), foreground=fg)
        t.tag_configure("strikethrough", overstrike=True, foreground=muted)
        t.tag_configure("code", font=("Consolas", 12), foreground=fg, background=code_bg)
        t.tag_configure("code_block", font=("Consolas", 12), foreground=fg,
                        background=code_bg, spacing1=5, spacing3=5, lmargin1=8, lmargin2=8)
        t.tag_configure("lang", foreground=link, font=("Consolas", 11, "italic"))
        t.tag_configure("blockquote", foreground=muted, background=quote_bg,
                        lmargin1=14, lmargin2=14, spacing1=2, spacing3=4)
        t.tag_configure("hr", foreground=hr_color)
        t.tag_configure("list", foreground=fg, spacing1=2, spacing3=2)
        t.tag_configure("link", foreground=link, underline=True)
        t.tag_configure("img", foreground=muted, font=("Microsoft YaHei UI", 12, "italic"),
                        background=code_bg, spacing1=4, spacing3=4)
        t.tag_configure("checkbox", foreground=muted, background=check_bg)
        t.tag_configure("checkbox_on", foreground=check_on, background=check_bg)
        t.tag_configure("para", spacing3=5, spacing1=1)

        # 光标所在行高亮（Typedown/Muya 编辑体验），置于最底层
        t.tag_configure("active_line", background=active_bg)
        t.tag_lower("active_line")

        # 优先级：行内代码 > 加粗 > 斜体 > 链接 > 删除线
        t.tag_raise("code")
        t.tag_raise("bold")
        t.tag_raise("italic")
        t.tag_raise("link")
        t.tag_raise("strikethrough")

    def apply_markdown_styles(self):
        """对编辑器当前内容实时应用渲染样式（不修改文本内容）"""
        t = self.text_widget
        for tag in self._style_tags:
            t.tag_remove(tag, "1.0", "end")
        content = t.get("1.0", "end-1c")
        if not content:
            return
        lines = content.split("\n")
        in_code = False
        for i, line in enumerate(lines):
            start = f"{i + 1}.0"
            end = f"{i + 1}.end"
            stripped = line.lstrip()
            indent = len(line) - len(stripped)  # 行首空白偏移

            # 代码块（含语言标签，参考 Muya）
            if stripped.startswith("```"):
                if not in_code and len(stripped) > 3:
                    t.tag_add("lang", f"{i + 1}.{indent + 3}", end)
                in_code = not in_code
                t.tag_add("code_block", start, end)
                continue
            if in_code:
                t.tag_add("code_block", start, end)
                continue

            # 标题
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                t.tag_add(f"h{min(level, 6)}", start, end)
                continue

            # 分隔线
            if re.match(r"^\s*(-{3,}|\*{3,})\s*$", line):
                t.tag_add("hr", start, end)
                continue

            # 引用
            if stripped.startswith(">"):
                t.tag_add("blockquote", start, end)
                continue

            # 任务列表（Typedown/Muya 渲染为复选框）
            m_task = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s", line)
            if m_task:
                t.tag_add("list", start, end)
                m_box = re.search(r"\[([ xX])\]", line)
                if m_box:
                    s = f"{i + 1}.{indent + m_box.start()}"
                    e = f"{i + 1}.{indent + m_box.end()}"
                    t.tag_add("checkbox_on" if m_box.group(1) in "xX" else "checkbox", s, e)
                self._apply_inline_styles(t, i, line)
                continue

            # 图片
            if re.search(r"!\[[^\]]*\]\([^)\s]+\)", line):
                t.tag_add("img", start, end)
                continue

            # 列表
            if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+[.)]\s", line):
                t.tag_add("list", start, end)
                self._apply_inline_styles(t, i, line)
                continue

            # 普通段落：GitHub 风格行距
            if line.strip():
                t.tag_add("para", start, end)
                self._apply_inline_styles(t, i, line)

    @staticmethod
    def _apply_inline_styles(t, row, line):
        """行内格式：**加粗**、*斜体*、~~删除线~~、`行内代码`、[链接](url)"""
        def rng(a, b):
            return f"{row + 1}.{a}", f"{row + 1}.{b}"

        for m in re.finditer(r"\*\*(.+?)\*\*", line):
            s, e = rng(m.start(), m.end())
            t.tag_add("bold", s, e)
        for m in re.finditer(r"(?<!\*)\*([^*]+?)\*(?!\*)", line):
            s, e = rng(m.start(), m.end())
            t.tag_add("italic", s, e)
        for m in re.finditer(r"~~(.+?)~~", line):
            s, e = rng(m.start(), m.end())
            t.tag_add("strikethrough", s, e)
        for m in re.finditer(r"`([^`]+)`", line):
            s, e = rng(m.start(), m.end())
            t.tag_add("code", s, e)
        for m in re.finditer(r"\[([^\]!]+)\]\(([^)\s]+)\)", line):
            s, e = rng(m.start(1), m.end(1))
            t.tag_add("link", s, e)

    def update_active_line(self, event=None):
        """高亮光标所在行（Typedown/Muya 编辑体验）"""
        t = self.text_widget
        try:
            idx = t.index("insert")
            row = int(idx.split(".")[0])
            t.tag_remove("active_line", "1.0", "end")
            t.tag_add("active_line", f"{row}.0", f"{row}.end")
        except tk.TclError:
            pass

    # ---------- 文本变更 ----------
    def on_text_change(self, event=None):
        self.apply_markdown_styles()
        self.update_outline()

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

    # ---------- 文件操作 ----------
    def new_file(self):
        if self.ask_save_if_dirty():
            self.edit_text.delete("1.0", "end")
            self.current_file = None
            self.update_title()
            self.apply_markdown_styles()
            self.update_outline()

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
            self.apply_markdown_styles()
            self.update_outline()

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
            html = markdown.markdown(content, extensions=["extra", "toc"])
            html_doc = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>156 Markdown</title></head>
<body>{html}</body>
</html>"""
            try:
                export_pdf(html_doc, path)
                messagebox.showinfo("导出成功", f"PDF 已保存至：{path}")
            except FileNotFoundError as e:
                messagebox.showerror("缺少 wkhtmltopdf", str(e))
            except Exception as e:
                messagebox.showerror("导出失败", f"生成 PDF 时出错：{e}")

        elif ext == ".docx":
            if not PYPANDOC_AVAILABLE:
                messagebox.showerror("缺少依赖", "导出 Word 需要安装 pypandoc，请运行：pip install pypandoc")
                return
            try:
                # 确保 pandoc 可用（自动下载或使用系统）
                pypandoc.ensure_pandoc_installed()
            except Exception as e:
                messagebox.showerror("Pandoc 错误", f"无法获取 Pandoc 转换器：{e}")
                return
            try:
                output = pypandoc.convert_text(
                    content,
                    'docx',
                    format='md',
                    extra_args=['--standalone']
                )
                with open(path, 'wb') as f:
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