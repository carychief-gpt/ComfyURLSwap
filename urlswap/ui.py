# -*- coding: utf-8 -*-
"""Tkinter 图形界面（深色现代主题）。"""
import os
import queue
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from . import classify
from . import project as proj
from .downloader import DownloadManager, _human
from .settings import load_settings, save_settings

# ---------------------------------------------------------------- 配色方案
BG        = "#17181d"   # 窗口底色
BG_CARD   = "#1f2129"   # 卡片
BG_INPUT  = "#262932"   # 输入区
BG_HOVER  = "#323642"
BORDER    = "#363b49"
FG        = "#e8eaf2"
FG_MUTED  = "#9aa1b5"
ACCENT    = "#7c5cff"   # 主题紫
ACCENT_H  = "#9078ff"
CYAN      = "#38bdf8"   # 进度条
GREEN     = "#3fb950"
RED       = "#f2555a"
ORANGE    = "#e3a008"

FONT_UI   = ("Microsoft YaHei UI", 10)
FONT_UI_B = ("Microsoft YaHei UI", 10, "bold")
FONT_MONO = ("Consolas", 10)

STATUS_CN = {
    "pending": "等待中", "downloading": "下载中", "paused": "已暂停",
    "done": "完成", "failed": "失败", "skipped": "已跳过", "canceled": "已取消",
}
CAT_CN = dict(classify.CATEGORIES)
HINT_TEXT = "把模型下载链接粘贴到这里，一行一条，例如：\n" \
            "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors\n" \
            "https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly-fp16.safetensors"


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _icon_candidates():
    root = _app_root()
    return [root / "app.ico", root / "tools" / "app.ico"]


# ---------------------------------------------------------------- 通用小部件
def flat_button(parent, text, command, kind="primary", tip=None):
    """扁平按钮（带悬停变色）。kind: primary / dark / ghost / danger / success"""
    kinds = {
        "primary": (ACCENT, ACCENT_H, "#ffffff"),
        "dark":    (BG_INPUT, BG_HOVER, FG),
        "ghost":   (BG_CARD, BG_HOVER, FG_MUTED),
        "danger":  ("#5c2b31", "#7a343c", "#ffb3b7"),
        "success": ("#1f5c34", "#287644", "#c8f5d8"),
    }
    bg, hover, fg = kinds[kind]
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                    activebackground=hover, activeforeground=fg,
                    relief="flat", bd=0, padx=14, pady=5, cursor="hand2",
                    font=("Microsoft YaHei UI", 9, "bold"),
                    highlightthickness=0, disabledforeground="#6b7280")

    def _enter(_e=None):
        if btn["state"] != "disabled":
            btn.configure(bg=hover)

    def _leave(_e=None):
        btn.configure(bg=bg)

    btn.bind("<Enter>", _enter)
    btn.bind("<Leave>", _leave)
    return btn


def make_text(parent, height, mono=False, readonly=False):
    """带样式滚动条的深色文本区，返回 (frame, text)。"""
    frame = tk.Frame(parent, bg=BG_INPUT,
                     highlightbackground=BORDER, highlightcolor=ACCENT,
                     highlightthickness=1)
    sb = ttk.Scrollbar(frame, orient="vertical")
    txt = tk.Text(frame, height=height, bg=BG_INPUT, fg=FG,
                  insertbackground=FG, relief="flat", bd=0, padx=8, pady=6,
                  font=FONT_MONO if mono else FONT_UI,
                  selectbackground=ACCENT, selectforeground="#ffffff",
                  wrap="char", yscrollcommand=sb.set)
    sb.configure(command=txt.yview)
    sb.pack(side="right", fill="y")
    txt.pack(side="left", fill="both", expand=True)
    if readonly:
        txt.configure(state="disabled")
    return frame, txt


def apply_theme(root):
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure(".", background=BG, foreground=FG, font=FONT_UI,
                 bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                 focuscolor=BG, fieldbackground=BG_INPUT)
    st.configure("TFrame", background=BG)
    st.configure("Card.TFrame", background=BG_CARD)
    st.configure("TLabel", background=BG, foreground=FG)
    st.configure("Muted.TLabel", background=BG, foreground=FG_MUTED)
    st.configure("Card.TLabel", background=BG_CARD, foreground=FG)
    st.configure("CardMuted.TLabel", background=BG_CARD, foreground=FG_MUTED)

    # 卡片（分组框）
    st.configure("Card.TLabelframe", background=BG_CARD,
                 bordercolor=BORDER, relief="flat", labelanchor="nw")
    st.configure("Card.TLabelframe.Label", background=BG_CARD,
                 foreground=ACCENT, font=("Microsoft YaHei UI", 10, "bold"))

    # 复选框 / 数字框 / 下拉框
    st.configure("TCheckbutton", background=BG_CARD, foreground=FG,
                 focuscolor=BG_CARD, indicatorspace=6)
    st.map("TCheckbutton",
           background=[("active", BG_CARD)],
           indicatorcolor=[("selected", ACCENT), ("!selected", BG_INPUT)])
    st.configure("TSpinbox", fieldbackground=BG_INPUT, background=BG_INPUT,
                 foreground=FG, arrowcolor=FG_MUTED, arrowsize=11,
                 insertcolor=FG, bordercolor=BORDER, padding=3)
    st.map("TSpinbox", fieldbackground=[("readonly", BG_INPUT)])
    st.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_INPUT,
                 foreground=FG, arrowcolor=FG_MUTED, arrowsize=13,
                 bordercolor=BORDER, padding=4)
    st.map("TCombobox",
           fieldbackground=[("readonly", BG_INPUT)],
           foreground=[("readonly", FG)],
           selectbackground=[("readonly", BG_INPUT)],
           selectforeground=[("readonly", FG)])
    root.option_add("*TCombobox*Listbox.background", BG_INPUT)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", FONT_UI)

    # 任务表格
    st.configure("Treeview", background=BG_INPUT, fieldbackground=BG_INPUT,
                 foreground=FG, rowheight=30, borderwidth=0,
                 font=("Consolas", 10))
    st.configure("Treeview.Heading", background=BG_CARD, foreground=FG_MUTED,
                 font=("Microsoft YaHei UI", 9, "bold"), relief="flat",
                 borderwidth=0, padding=6)
    st.map("Treeview", background=[("selected", "#3a3f52")],
           foreground=[("selected", "#ffffff")])
    st.map("Treeview.Heading", background=[("active", BG_HOVER)])

    # 细滚动条
    for orient in ("Vertical", "Horizontal"):
        st.configure(orient + ".TScrollbar", background="#4a5062",
                     troughcolor=BG_INPUT, borderwidth=0, arrowsize=0,
                     relief="flat", width=10, sliderrelief="flat")
        st.map(orient + ".TScrollbar", background=[("active", "#5a6178")])

    # 纤细进度条
    st.configure("Slim.Horizontal.TProgressbar", troughcolor=BG_INPUT,
                 background=CYAN, borderwidth=0, thickness=6)
    return st


# ---------------------------------------------------------------- 分类弹窗
class CategoryDialog(tk.Toplevel):
    def __init__(self, master, current):
        super().__init__(master)
        self.configure(bg=BG)
        self.title("选择模型分类")
        self.resizable(False, False)
        self.result = None
        tk.Label(self, text="下载完成后放入 models 下的哪个目录：",
                 bg=BG, fg=FG, font=FONT_UI).pack(padx=16, pady=(16, 6))
        labels = ["%s — %s" % (k, v) for k, v in classify.CATEGORIES]
        cur = "%s — %s" % (current, CAT_CN.get(current, current))
        self.var = tk.StringVar(value=cur if cur in labels else labels[0])
        cbf = tk.Frame(self, bg=BG)
        cbf.pack(padx=16, pady=(0, 14))
        cb = ttk.Combobox(cbf, textvariable=self.var, values=labels,
                          state="readonly", width=34, font=FONT_UI)
        cb.pack()
        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(0, 16))
        flat_button(btns, "确定", self._ok, "primary").pack(side="left", padx=6)
        flat_button(btns, "取消", self.destroy, "dark").pack(side="left", padx=6)
        self.grab_set()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
            self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        except tk.TclError:
            pass

    def _ok(self):
        self.result = self.var.get().split(" — ")[0]
        self.destroy()


# ---------------------------------------------------------------- 主窗口
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ComfyURLSwap · ComfyUI 模型下载器")
        self.configure(bg=BG)
        self.geometry("1180x800")
        self.minsize(960, 660)
        apply_theme(self)
        try:
            for ico in _icon_candidates():
                if ico.exists():
                    self.iconbitmap(str(ico))
                    break
        except tk.TclError:
            pass

        self.settings = load_settings()
        self.models_dir = None
        self._log_q = queue.Queue()
        self._tree_map = {}
        self._rows = {}
        self._hint_shown = True

        self.manager = DownloadManager(
            self.settings, lambda: self.models_dir,
            on_event=lambda m: self._log_q.put(m))

        self._build_ui()
        self._init_projects()
        self.manager.load()
        self._log_q.put("提示：双击任务行可以修改模型分类（下载前/暂停时可用）。")
        self._sync_tree()
        self.after(300, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- UI 构建
    def _build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=2)
        root.rowconfigure(3, weight=4)

        # --- 顶部标题栏 -----------------------------------------------------
        head = tk.Frame(root, bg=BG)
        head.grid(row=0, sticky="ew", pady=(6, 12))
        logo = tk.Canvas(head, width=38, height=38, bg=BG, highlightthickness=0)
        logo.create_oval(3, 3, 35, 35, fill=ACCENT, outline="")
        logo.create_text(19, 16, text="↓", fill="#ffffff",
                         font=("Arial", 16, "bold"))
        logo.create_line(11, 27, 27, 27, fill="#ffffff", width=3)
        logo.pack(side="left", padx=(2, 10))
        tk.Label(head, text="ComfyURLSwap", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 17, "bold")).pack(side="left")
        tk.Label(head, text="ComfyUI 模型批量下载 · HF 镜像加速 · 断点续传",
                 bg=BG, fg=FG_MUTED, font=("Microsoft YaHei UI", 10)).pack(
            side="left", padx=(12, 0), pady=(6, 0))
        tk.Label(head, text="v" + __version__, bg=BG, fg="#565c6e",
                 font=("Consolas", 9)).pack(side="right", pady=(8, 0))

        # --- 1. 项目选择 ----------------------------------------------------
        pf = ttk.LabelFrame(root, text=" 1. ComfyUI 项目 ", style="Card.TLabelframe")
        pf.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        pf.columnconfigure(1, weight=1)
        body = ttk.Frame(pf, style="Card.TFrame")
        body.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10,
                  pady=(2, 4))
        body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text="项目路径", bg=BG_CARD, fg=FG_MUTED,
                 font=FONT_UI).grid(row=0, column=0, sticky="w")
        row = ttk.Frame(body, style="Card.TFrame")
        row.grid(row=1, column=0, sticky="ew", pady=(3, 2))
        row.columnconfigure(0, weight=1)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(row, textvariable=self.project_var,
                                          state="readonly", font=FONT_UI)
        self.project_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.project_combo.bind("<<ComboboxSelected>>",
                                lambda e: self._apply_project(self.project_var.get()))
        flat_button(row, "浏览…", self._browse, "dark").grid(row=0, column=1, padx=3)
        flat_button(row, "重新检测", self._redetect, "dark").grid(row=0, column=2, padx=3)
        self.dir_label = tk.Label(body, text="模型目录: 未选择", bg=BG_CARD,
                                  fg=RED, font=("Microsoft YaHei UI", 9))
        self.dir_label.grid(row=2, column=0, sticky="w")
        # 让卡片内容区撑开
        pf.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        # --- 2. URL 输入 -----------------------------------------------------
        uf = ttk.LabelFrame(
            root,
            text=" 2. 模型下载地址（一行一条，自动 huggingface.co → hf-mirror.com ） ",
            style="Card.TLabelframe")
        uf.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        uf.columnconfigure(0, weight=1)
        uf.rowconfigure(1, weight=1)
        self.url_frame, self.url_text = make_text(uf, 5)
        self.url_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 4))
        self.url_text.insert("1.0", HINT_TEXT)
        self.url_text.configure(foreground="#6f7688")
        self.url_text.bind("<FocusIn>", self._clear_hint)
        self.url_text.bind("<FocusOut>", self._show_hint)

        opts = ttk.Frame(uf, style="Card.TFrame")
        opts.grid(row=2, column=0, sticky="ew", padx=6, pady=(2, 8))
        flat_button(opts, "＋ 添加并开始下载", self._add_urls, "primary")\
            .pack(side="left", padx=4)
        self.mirror_var = tk.BooleanVar(value=bool(self.settings.get("auto_mirror", True)))
        ttk.Checkbutton(opts, text="自动替换为 hf-mirror.com",
                        variable=self.mirror_var, command=self._save_opts)\
            .pack(side="left", padx=8)
        self.skip_var = tk.BooleanVar(value=bool(self.settings.get("skip_existing", True)))
        ttk.Checkbutton(opts, text="跳过已存在文件",
                        variable=self.skip_var, command=self._save_opts)\
            .pack(side="left", padx=8)
        ttk.Label(opts, text="线程数").pack(side="left", padx=(14, 3))
        self.workers_var = tk.IntVar(value=int(self.settings.get("workers", 4)))
        ttk.Spinbox(opts, from_=1, to=16, width=4, textvariable=self.workers_var,
                    command=self._save_opts, font=FONT_UI).pack(side="left")
        flat_button(opts, "清空输入",
                    lambda: self.url_text.delete("1.0", "end"), "ghost")\
            .pack(side="right", padx=6)
        root.rowconfigure(2, weight=0)

        # --- 3. 任务表 --------------------------------------------------------
        tf = ttk.LabelFrame(root, text=" 3. 下载任务（双击可修改分类） ",
                            style="Card.TLabelframe")
        tf.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)
        cols = ("name", "cat", "status", "prog", "speed", "size", "msg")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 selectmode="extended")
        headers = [("name", "文件名", 380, True), ("cat", "分类", 105, False),
                   ("status", "状态", 66, False), ("prog", "进度", 150, False),
                   ("speed", "速度", 82, False), ("size", "大小", 112, False),
                   ("msg", "备注", 190, True)]
        for cid, text, width, stretch in headers:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=width, stretch=stretch, anchor="w")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(4, 6))
        vsb.grid(row=0, column=1, sticky="ns", pady=(4, 6), padx=(0, 3))
        self.tree.bind("<Double-1>", lambda e: self._change_cat())
        # 状态行颜色
        self.tree.tag_configure("downloading", foreground=CYAN)
        self.tree.tag_configure("done", foreground="#7ee2a0")
        self.tree.tag_configure("failed", foreground="#ff8a8f")
        self.tree.tag_configure("paused", foreground="#e3c078")
        self.tree.tag_configure("skipped", foreground=FG_MUTED)
        self.tree.tag_configure("canceled", foreground="#7a8095")
        self.tree.tag_configure("pending", foreground=FG)

        btns = ttk.Frame(root, style="Card.TFrame")
        btns.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        flat_button(btns, "▶ 开始/继续", self._start, "success").pack(side="left", padx=3)
        flat_button(btns, "⏸ 暂停全部", self._pause, "dark").pack(side="left", padx=3)
        flat_button(btns, "↻ 重试失败", self._retry, "dark").pack(side="left", padx=3)
        flat_button(btns, "✕ 取消选中", self._cancel_sel, "danger").pack(side="left", padx=3)
        flat_button(btns, "✎ 修改分类", self._change_cat, "dark").pack(side="left", padx=3)
        flat_button(btns, "🧹 移除已完成", self._remove_done, "ghost").pack(side="left", padx=3)
        flat_button(btns, "📁 打开模型目录", self._open_dir, "primary").pack(side="right", padx=3)

        # --- 状态栏 -----------------------------------------------------------
        bar = tk.Frame(root, bg=BG_CARD, highlightbackground=BORDER,
                       highlightthickness=1)
        bar.grid(row=5, column=0, sticky="ew", pady=(0, 6))
        self.stat_label = tk.Label(bar, text="准备就绪", bg=BG_CARD,
                                   fg=FG_MUTED, font=("Microsoft YaHei UI", 9))
        self.stat_label.pack(side="left", padx=10, pady=4)
        self.gspeed_label = tk.Label(bar, text="", bg=BG_CARD, fg=CYAN,
                                     font=("Consolas", 9, "bold"))
        self.gspeed_label.pack(side="left", padx=8)
        self.gprog = ttk.Progressbar(bar, style="Slim.Horizontal.TProgressbar",
                                     length=240, maximum=100)
        self.gprog.pack(side="right", padx=(6, 4))
        self.gprog_label = tk.Label(bar, text="", bg=BG_CARD, fg=FG_MUTED,
                                    font=("Consolas", 9))
        self.gprog_label.pack(side="right", padx=4)

        # --- 日志 -------------------------------------------------------------
        lf = ttk.LabelFrame(root, text=" 日志 ", style="Card.TLabelframe")
        lf.grid(row=6, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        self.log_frame, self.log = make_text(lf, 7, mono=True, readonly=True)
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=8,
                            pady=(2, 6))
        root.rowconfigure(6, weight=2)

    # ------------------------------------------------------------- 项目相关
    def _init_projects(self):
        saved = [p for p in self.settings.get("projects", []) if Path(p).is_dir()]
        try:
            detected = proj.auto_detect()
        except OSError:
            detected = []
        merged = list(dict.fromkeys(detected + saved))
        self._set_values(merged)
        last = self.settings.get("last_project", "")
        if last in merged:
            pick = last
        elif merged:
            pick = merged[0]
        else:
            pick = ""
        self.project_combo.set(pick)
        if pick:
            self._apply_project(pick, silent=True)
        else:
            self._log("未自动检测到 ComfyUI 项目，请点击“浏览…”手动选择项目目录。")

    def _set_values(self, paths):
        self.project_combo["values"] = paths

    def _apply_project(self, path, silent=False):
        if not path:
            return
        md = proj.models_dir_of(path)
        if md is None:
            self.models_dir = None
            self.dir_label.config(
                text="⚠ 所选项目内未找到 ComfyUI/models，请重新选择", fg=RED)
            return
        self.models_dir = str(md)
        self.dir_label.config(text="✔ 模型目录:  %s" % self.models_dir,
                              fg=GREEN)
        s = self.settings
        s["last_project"] = path
        projects = list(dict.fromkeys([path] + list(s.get("projects", []))))
        s["projects"] = projects
        save_settings(s)
        if not silent:
            self._log("已选择项目: %s" % path)

    def _browse(self):
        d = filedialog.askdirectory(title="选择 ComfyUI 项目目录")
        if not d:
            return
        p = Path(d)
        if not proj.looks_like_project(p):
            if not messagebox.askyesno(
                    "提示",
                    "所选目录里没有找到 ComfyUI\\models 或 models 结构。\n\n"
                    "是否在该目录下新建 ComfyUI\\models 并使用它？"):
                return
        try:
            proj.ensure_models_dir(p)
        except OSError as e:
            messagebox.showerror("错误", "创建目录失败: %s" % e)
            return
        values = list(self.project_combo["values"])
        rp = str(p.resolve())
        if rp not in values:
            values.insert(0, rp)
            self._set_values(values)
        self.project_combo.set(rp)
        self._apply_project(rp)

    def _redetect(self):
        saved = [p for p in self.settings.get("projects", []) if Path(p).is_dir()]
        try:
            detected = proj.auto_detect()
        except OSError:
            detected = []
        merged = list(dict.fromkeys(detected + saved))
        self._set_values(merged)
        cur = self.project_var.get()
        if not cur and merged:
            self.project_combo.set(merged[0])
            self._apply_project(merged[0])
        self._log("重新检测完成，共找到 %d 个项目。" % len(merged))

    # ------------------------------------------------------------- URL 任务
    def _clear_hint(self, _e=None):
        if self._hint_shown:
            self.url_text.delete("1.0", "end")
            self.url_text.configure(foreground=FG)
            self._hint_shown = False

    def _show_hint(self, _e=None):
        if not self.url_text.get("1.0", "end").strip():
            self.url_text.delete("1.0", "end")
            self.url_text.insert("1.0", HINT_TEXT)
            self.url_text.configure(foreground="#6f7688")
            self._hint_shown = True

    def _add_urls(self):
        text = self.url_text.get("1.0", "end")
        if self._hint_shown:
            text = ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            messagebox.showinfo("提示", "请先粘贴下载链接，一行一条。")
            return
        try:
            added = self.manager.add_tasks(lines, auto_mirror=self.mirror_var.get())
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return
        if added:
            self.url_text.delete("1.0", "end")
            self._hint_shown = True
            self._start()
        self._sync_tree()

    # ------------------------------------------------------------- 控制按钮
    def _start(self):
        if self.models_dir is None and not self.manager.has_active():
            messagebox.showerror("错误", "请先在第 1 步选择 ComfyUI 项目。")
            return
        self._save_opts()
        self.manager.start(self.workers_var.get())

    def _pause(self):
        self.manager.stop()
        self._log("已暂停全部下载（字节级断点已保留，点击“开始/继续”自动续传）。")

    def _retry(self):
        n = self.manager.retry_failed()
        if n:
            self._log("重新加入队列: %d 个任务" % n)
            self.manager.start(self.workers_var.get())
        else:
            self._log("没有失败/已取消的任务。")

    def _remove_done(self):
        n = self.manager.remove_completed()
        self._log("已移除 %d 条任务记录。" % n if n else "没有可移除的已完成任务。")
        self._sync_tree()

    def _cancel_sel(self):
        for iid in self.tree.selection():
            tid = self._tid(iid)
            if tid:
                self.manager.cancel(tid)
        self._sync_tree()

    def _change_cat(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先在任务列表中选中一个任务。")
            return
        tid = self._tid(sel[0])
        t = self.manager.find(tid) if tid else None
        if not t:
            return
        dlg = CategoryDialog(self, t.category)
        self.wait_window(dlg)
        if dlg.result and dlg.result != t.category:
            if self.manager.set_category(tid, dlg.result):
                self._log("任务 %s 分类改为 %s" % (t.filename, dlg.result))
                self._sync_tree()
            else:
                messagebox.showinfo("提示", "该任务正在下载中，无法修改分类。")

    def _open_dir(self):
        if not self.models_dir:
            messagebox.showinfo("提示", "尚未选择项目。")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(self.models_dir)
            else:
                messagebox.showinfo("提示", self.models_dir)
        except OSError as e:
            messagebox.showerror("错误", str(e))

    # ------------------------------------------------------------- 刷新循环
    def _tid(self, iid):
        for tid, i in self._tree_map.items():
            if i == iid:
                return tid
        return None

    def _tick(self):
        try:
            while True:
                self._log(self._log_q.get_nowait())
        except queue.Empty:
            pass
        self._sync_tree()
        self._update_bar()
        self.after(400, self._tick)

    @staticmethod
    def _bar(pct):
        n = max(0, min(10, round(pct / 10)))
        return "█" * n + "░" * (10 - n)

    def _sync_tree(self):
        snap = self.manager.snapshot()
        live = set()
        for t in snap:
            iid = self._tree_map.get(t["id"])
            if iid is None or not self.tree.exists(iid):
                iid = self.tree.insert("", "end", values=("",) * 7)
                self._tree_map[t["id"]] = iid
                self._rows.pop(iid, None)
            total = t["total"]
            done = t["downloaded"]
            if total:
                pct = done * 100 // total
                prog = "%s %3d%%" % (self._bar(pct), pct)
            elif done:
                prog = _human(done)
            else:
                prog = "-"
            speed = (_human(t["speed"]) + "/s"
                     if t["status"] == "downloading" and t["speed"] else "-")
            size = ("%s / %s" % (_human(done), _human(total))) if total else _human(done)
            vals = (t["filename"], CAT_CN.get(t["category"], t["category"]),
                    STATUS_CN.get(t["status"], t["status"]), prog, speed, size,
                    t["error"] or ("→ models/%s/" % t["category"]
                                   if t["status"] in ("done", "skipped") else ""))
            if self._rows.get(iid) != vals:
                self.tree.item(iid, values=vals, tags=(t["status"],))
                self._rows[iid] = vals
            live.add(iid)
        for iid in list(self.tree.get_children()):
            if iid not in live:
                self.tree.delete(iid)
                self._rows.pop(iid, None)
        for iid in self._tree_map.values():
            if not self.tree.exists(iid):
                self._rows.pop(iid, None)
        self._tree_map = {k: v for k, v in self._tree_map.items()
                          if self.tree.exists(v)}
        self._snap_cache = snap

    def _update_bar(self):
        snap = getattr(self, "_snap_cache", []) or []
        cnt = {"done": 0, "failed": 0, "downloading": 0, "pending": 0,
               "paused": 0, "skipped": 0, "canceled": 0}
        for t in snap:
            if t["status"] in cnt:
                cnt[t["status"]] += 1
        tot_bytes = sum(max(t["total"], t["downloaded"]) for t in snap)
        done_bytes = sum(t["downloaded"] for t in snap)
        gs = sum(t["speed"] for t in snap if t["status"] == "downloading")
        pct = int(done_bytes * 100 / tot_bytes) if tot_bytes else 0
        parts = ["总计 %d" % len(snap)]
        if cnt["done"]:
            parts.append("完成 %d" % cnt["done"])
        if cnt["skipped"]:
            parts.append("跳过 %d" % cnt["skipped"])
        if cnt["downloading"]:
            parts.append("下载中 %d" % cnt["downloading"])
        if cnt["pending"]:
            parts.append("等待 %d" % cnt["pending"])
        if cnt["paused"]:
            parts.append("暂停 %d" % cnt["paused"])
        if cnt["failed"]:
            parts.append("失败 %d" % cnt["failed"])
        self.stat_label.config(text="   ".join(parts) if snap else "准备就绪")
        self.gspeed_label.config(text=("总速度 %s/s" % _human(gs)) if gs else "")
        self.gprog["value"] = pct
        self.gprog_label.config(text="总进度 %d%%" % pct if snap else "")

    # ------------------------------------------------------------- 其它
    def _save_opts(self):
        s = self.settings
        s["workers"] = int(self.workers_var.get() or 4)
        s["skip_existing"] = bool(self.skip_var.get())
        s["auto_mirror"] = bool(self.mirror_var.get())
        save_settings(s)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", time.strftime("[%H:%M:%S] ") + msg + "\n")
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > 600:
            self.log.delete("1.0", "%d.0" % (lines - 400))
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_close(self):
        if self.manager.has_active():
            if not messagebox.askyesno(
                    "确认退出",
                    "还有未完成的下载任务。\n\n退出后断点会保留，"
                    "下次打开程序自动恢复，继续吗？"):
                return
        self.manager.stop()
        self._save_opts()
        self.destroy()


def run():
    App().mainloop()
    return 0
