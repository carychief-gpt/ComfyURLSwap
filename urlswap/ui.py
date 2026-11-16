# -*- coding: utf-8 -*-
"""Tkinter 图形界面（深色现代主题 + 多语言 i18n）。"""
import os
import queue
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import classify
from . import i18n
from . import project as proj
from .downloader import DownloadManager, _human
from .i18n import LANGUAGES, tr
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

FONT_UI   = ("Microsoft YaHei UI", 10)
FONT_MONO = ("Consolas", 10)

_STATUS_KEYS = ("pending", "downloading", "paused", "done", "failed",
                "skipped", "canceled")


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _icon_candidates():
    root = _app_root()
    return [root / "app.ico", root / "tools" / "app.ico"]


# ---------------------------------------------------------------- 通用小部件
def flat_button(parent, text, command, kind="primary"):
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

    st.configure("Card.TLabelframe", background=BG_CARD,
                 bordercolor=BORDER, relief="flat", labelanchor="nw")
    st.configure("Card.TLabelframe.Label", background=BG_CARD,
                 foreground=ACCENT, font=("Microsoft YaHei UI", 10, "bold"))

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

    st.configure("Treeview", background=BG_INPUT, fieldbackground=BG_INPUT,
                 foreground=FG, rowheight=30, borderwidth=0,
                 font=("Consolas", 10))
    st.configure("Treeview.Heading", background=BG_CARD, foreground=FG_MUTED,
                 font=("Microsoft YaHei UI", 9, "bold"), relief="flat",
                 borderwidth=0, padding=6)
    st.map("Treeview", background=[("selected", "#3a3f52")],
           foreground=[("selected", "#ffffff")])
    st.map("Treeview.Heading", background=[("active", BG_HOVER)])

    for orient in ("Vertical", "Horizontal"):
        st.configure(orient + ".TScrollbar", background="#4a5062",
                     troughcolor=BG_INPUT, borderwidth=0, arrowsize=0,
                     relief="flat", width=10, sliderrelief="flat")
        st.map(orient + ".TScrollbar", background=[("active", "#5a6178")])

    st.configure("Slim.Horizontal.TProgressbar", troughcolor=BG_INPUT,
                 background=CYAN, borderwidth=0, thickness=6)
    return st


# ---------------------------------------------------------------- 分类弹窗
class CategoryDialog(tk.Toplevel):
    def __init__(self, master, current):
        super().__init__(master)
        self.configure(bg=BG)
        self.title(tr("dlg.cat_title"))
        self.resizable(False, False)
        self.result = None
        tk.Label(self, text=tr("dlg.cat_q"), bg=BG, fg=FG,
                 font=FONT_UI).pack(padx=16, pady=(16, 6))
        labels = [tr("cat." + k) for k in classify.CATEGORIES]
        cur = tr("cat." + current)
        self.var = tk.StringVar(value=cur if cur in labels else labels[0])
        cbf = tk.Frame(self, bg=BG)
        cbf.pack(padx=16, pady=(0, 14))
        cb = ttk.Combobox(cbf, textvariable=self.var, values=labels,
                          state="readonly", width=34, font=FONT_UI)
        cb.pack()
        btns = tk.Frame(self, bg=BG)
        btns.pack(pady=(0, 16))
        flat_button(btns, tr("dlg.ok"), self._ok, "primary").pack(side="left", padx=6)
        flat_button(btns, tr("dlg.cancel"), self.destroy, "dark").pack(side="left", padx=6)
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
        idx = [tr("cat." + k) for k in classify.CATEGORIES].index(self.var.get())
        self.result = classify.CATEGORIES[idx]
        self.destroy()


# ---------------------------------------------------------------- 主窗口
class App(tk.Tk):
    def __init__(self):
        super().__init__()
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
        lang = self.settings.get("language") or i18n.detect_language()
        i18n.set_language(lang)
        self.title(tr("app.title"))

        self.models_dir = None
        self._log_q = queue.Queue()
        self._tree_map = {}
        self._rows = {}
        self._hint_shown = True
        self._log_lines = []
        self.content = None

        self.manager = DownloadManager(
            self.settings, lambda: self.models_dir,
            on_event=lambda m: self._log_q.put(m))

        self._build_ui()
        self._init_projects()
        self.manager.load()
        self._log_q.put(tr("log.tip"))
        self._sync_tree()
        self.after(300, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- UI 构建
    def _build_ui(self):
        if self.content is not None:
            self.content.destroy()
            self._tree_map.clear()
            self._rows.clear()
        root = ttk.Frame(self)
        self.content = root
        root.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)
        root.rowconfigure(2, weight=2)
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
        tk.Label(head, text=tr("app.subtitle"), bg=BG, fg=FG_MUTED,
                 font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(12, 0),
                                                       pady=(6, 0))
        tk.Label(head, text="v" + self._version(), bg=BG, fg="#565c6e",
                 font=("Consolas", 9)).pack(side="right", padx=(6, 0), pady=(8, 0))
        # 语言选择下拉
        lang_names = [name for _code, name in LANGUAGES]
        self._lang_names = lang_names
        self._lang_codes = [code for code, _name in LANGUAGES]
        self.lang_var = tk.StringVar(
            value=lang_names[self._lang_codes.index(i18n.get_language())])
        lang_cb = ttk.Combobox(head, textvariable=self.lang_var,
                               values=lang_names, state="readonly", width=10,
                               font=("Microsoft YaHei UI", 9))
        lang_cb.pack(side="right", padx=(4, 2), pady=(5, 0))
        lang_cb.bind("<<ComboboxSelected>>", self._on_lang_selected)

        # --- 1. 项目选择 ----------------------------------------------------
        pf = ttk.LabelFrame(root, text=tr("sec.project"), style="Card.TLabelframe")
        pf.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        pf.columnconfigure(1, weight=1)
        body = ttk.Frame(pf, style="Card.TFrame")
        body.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10,
                  pady=(2, 4))
        body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text=tr("lbl.project_path"), bg=BG_CARD, fg=FG_MUTED,
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
        flat_button(row, tr("btn.browse"), self._browse, "dark").grid(row=0, column=1, padx=3)
        flat_button(row, tr("btn.redetect"), self._redetect, "dark").grid(row=0, column=2, padx=3)
        self.dir_label = tk.Label(body, text=tr("dir.none"), bg=BG_CARD,
                                  fg=RED, font=("Microsoft YaHei UI", 9))
        self.dir_label.grid(row=2, column=0, sticky="w")
        pf.rowconfigure(0, weight=1)

        # --- 2. URL 输入 -----------------------------------------------------
        uf = ttk.LabelFrame(root, text=tr("sec.urls"), style="Card.TLabelframe")
        uf.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        uf.columnconfigure(0, weight=1)
        uf.rowconfigure(1, weight=1)
        self.url_frame, self.url_text = make_text(uf, 5)
        self.url_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 4))
        self.url_text.insert("1.0", tr("hint.urls"))
        self.url_text.configure(foreground="#6f7688")
        self.url_text.bind("<FocusIn>", self._clear_hint)
        self.url_text.bind("<FocusOut>", self._show_hint)

        opts = ttk.Frame(uf, style="Card.TFrame")
        opts.grid(row=2, column=0, sticky="ew", padx=6, pady=(2, 8))
        flat_button(opts, tr("btn.add"), self._add_urls, "primary")\
            .pack(side="left", padx=4)
        self.mirror_var = tk.BooleanVar(value=bool(self.settings.get("auto_mirror", True)))
        ttk.Checkbutton(opts, text=tr("chk.mirror"),
                        variable=self.mirror_var, command=self._save_opts)\
            .pack(side="left", padx=8)
        self.skip_var = tk.BooleanVar(value=bool(self.settings.get("skip_existing", True)))
        ttk.Checkbutton(opts, text=tr("chk.skip"),
                        variable=self.skip_var, command=self._save_opts)\
            .pack(side="left", padx=8)
        ttk.Label(opts, text=tr("lbl.threads")).pack(side="left", padx=(14, 3))
        self.workers_var = tk.IntVar(value=int(self.settings.get("workers", 4)))
        ttk.Spinbox(opts, from_=1, to=16, width=4, textvariable=self.workers_var,
                    command=self._save_opts, font=FONT_UI).pack(side="left")
        flat_button(opts, tr("btn.clear"),
                    lambda: self.url_text.delete("1.0", "end"), "ghost")\
            .pack(side="right", padx=6)

        # --- 3. 任务表 --------------------------------------------------------
        tf = ttk.LabelFrame(root, text=tr("sec.tasks"), style="Card.TLabelframe")
        tf.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)
        cols = ("name", "cat", "status", "prog", "speed", "size", "msg")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 selectmode="extended")
        headers = [("name", tr("col.name"), 380, True),
                   ("cat", tr("col.cat"), 130, False),
                   ("status", tr("col.status"), 80, False),
                   ("prog", tr("col.prog"), 150, False),
                   ("speed", tr("col.speed"), 82, False),
                   ("size", tr("col.size"), 112, False),
                   ("msg", tr("col.msg"), 180, True)]
        for cid, text, width, stretch in headers:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=width, stretch=stretch, anchor="w")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(4, 6))
        vsb.grid(row=0, column=1, sticky="ns", pady=(4, 6), padx=(0, 3))
        self.tree.bind("<Double-1>", lambda e: self._change_cat())
        self.tree.tag_configure("downloading", foreground=CYAN)
        self.tree.tag_configure("done", foreground="#7ee2a0")
        self.tree.tag_configure("failed", foreground="#ff8a8f")
        self.tree.tag_configure("paused", foreground="#e3c078")
        self.tree.tag_configure("skipped", foreground=FG_MUTED)
        self.tree.tag_configure("canceled", foreground="#7a8095")
        self.tree.tag_configure("pending", foreground=FG)

        btns = ttk.Frame(root, style="Card.TFrame")
        btns.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        flat_button(btns, tr("btn.start"), self._start, "success").pack(side="left", padx=3)
        flat_button(btns, tr("btn.pause"), self._pause, "dark").pack(side="left", padx=3)
        flat_button(btns, tr("btn.retry"), self._retry, "dark").pack(side="left", padx=3)
        flat_button(btns, tr("btn.cancel_sel"), self._cancel_sel, "danger").pack(side="left", padx=3)
        flat_button(btns, tr("btn.chcat"), self._change_cat, "dark").pack(side="left", padx=3)
        flat_button(btns, tr("btn.rmdone"), self._remove_done, "ghost").pack(side="left", padx=3)
        flat_button(btns, tr("btn.opend"), self._open_dir, "primary").pack(side="right", padx=3)

        # --- 状态栏 -----------------------------------------------------------
        bar = tk.Frame(root, bg=BG_CARD, highlightbackground=BORDER,
                       highlightthickness=1)
        bar.grid(row=5, column=0, sticky="ew", pady=(0, 6))
        self.stat_label = tk.Label(bar, text=tr("st.ready"), bg=BG_CARD,
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
        lf = ttk.LabelFrame(root, text=tr("sec.log"), style="Card.TLabelframe")
        lf.grid(row=6, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        self.log_frame, self.log = make_text(lf, 7, mono=True, readonly=True)
        self.log_frame.grid(row=0, column=0, sticky="nsew", padx=8,
                            pady=(2, 6))
        root.rowconfigure(6, weight=2)

        # 语言切换重建后恢复历史日志
        if self._log_lines:
            self.log.configure(state="normal")
            for line in self._log_lines[-400:]:
                self.log.insert("end", line + "\n")
            self.log.configure(state="disabled")
            self.log.see("end")

    @staticmethod
    def _version():
        from . import __version__
        return __version__

    # ---------------------------------------------------------------- 语言切换
    def _on_lang_selected(self, _e=None):
        idx = self._lang_names.index(self.lang_var.get())
        code = self._lang_codes[idx]
        if code == i18n.get_language():
            return
        i18n.set_language(code)
        self.settings["language"] = code
        save_settings(self.settings)
        self.title(tr("app.title"))
        keep_dir = self.models_dir
        keep_project = self.project_var.get()
        self._build_ui()
        self._set_projects(self._merged_projects())
        if keep_project:
            self.project_combo.set(keep_project)
        if keep_dir:
            self._apply_project(keep_project, silent=True)
        self._sync_tree()

    # ------------------------------------------------------------- 项目相关
    def _merged_projects(self):
        saved = [p for p in self.settings.get("projects", []) if Path(p).is_dir()]
        try:
            detected = proj.auto_detect()
        except OSError:
            detected = []
        return list(dict.fromkeys(detected + saved))

    def _init_projects(self):
        merged = self._merged_projects()
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
            self._log(tr("dir.none") + " — " + tr("btn.browse"))

    def _set_projects(self, paths):
        self._set_values(paths)

    def _set_values(self, paths):
        self.project_combo["values"] = paths

    def _apply_project(self, path, silent=False):
        if not path:
            return
        md = proj.models_dir_of(path)
        if md is None:
            self.models_dir = None
            self.dir_label.config(text=tr("dir.missing"), fg=RED)
            return
        self.models_dir = str(md)
        self.dir_label.config(text=tr("dir.ok", self.models_dir), fg=GREEN)
        s = self.settings
        s["last_project"] = path
        projects = list(dict.fromkeys([path] + list(s.get("projects", []))))
        s["projects"] = projects
        save_settings(s)
        if not silent:
            self._log(tr("log.project", path))

    def _browse(self):
        d = filedialog.askdirectory(title=tr("msg.browse_title"))
        if not d:
            return
        p = Path(d)
        if not proj.looks_like_project(p):
            if not messagebox.askyesno(tr("msg.notice"), tr("msg.browse_ask")):
                return
        try:
            proj.ensure_models_dir(p)
        except OSError as e:
            messagebox.showerror(tr("msg.err"), tr("msg.mkfail", e))
            return
        values = list(self.project_combo["values"])
        rp = str(p.resolve())
        if rp not in values:
            values.insert(0, rp)
            self._set_values(values)
        self.project_combo.set(rp)
        self._apply_project(rp)

    def _redetect(self):
        merged = self._merged_projects()
        self._set_values(merged)
        cur = self.project_var.get()
        if not cur and merged:
            self.project_combo.set(merged[0])
            self._apply_project(merged[0])
        self._log(tr("log.redetect", len(merged)))

    # ------------------------------------------------------------- URL 任务
    def _clear_hint(self, _e=None):
        if self._hint_shown:
            self.url_text.delete("1.0", "end")
            self.url_text.configure(foreground=FG)
            self._hint_shown = False

    def _show_hint(self, _e=None):
        if not self.url_text.get("1.0", "end").strip():
            self.url_text.delete("1.0", "end")
            self.url_text.insert("1.0", tr("hint.urls"))
            self.url_text.configure(foreground="#6f7688")
            self._hint_shown = True

    def _add_urls(self):
        text = self.url_text.get("1.0", "end")
        if self._hint_shown:
            text = ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            messagebox.showinfo(tr("msg.info"), tr("msg.no_urls"))
            return
        try:
            added = self.manager.add_tasks(lines, auto_mirror=self.mirror_var.get())
        except ValueError as e:
            messagebox.showerror(tr("msg.err"), str(e))
            return
        if added:
            self.url_text.delete("1.0", "end")
            self._hint_shown = True
            self._start()
        self._sync_tree()

    # ------------------------------------------------------------- 控制按钮
    def _start(self):
        if self.models_dir is None and not self.manager.has_active():
            messagebox.showerror(tr("msg.err"), tr("msg.no_project"))
            return
        self._save_opts()
        self.manager.start(self.workers_var.get())

    def _pause(self):
        self.manager.stop()

    def _retry(self):
        n = self.manager.retry_failed()
        if n:
            self._log(tr("msg.requeued", n))
            self.manager.start(self.workers_var.get())
        else:
            self._log(tr("msg.no_failed"))

    def _remove_done(self):
        n = self.manager.remove_completed()
        self._log(tr("msg.removed", n) if n else tr("msg.nothing"))
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
            messagebox.showinfo(tr("msg.info"), tr("msg.select_first"))
            return
        tid = self._tid(sel[0])
        t = self.manager.find(tid) if tid else None
        if not t:
            return
        dlg = CategoryDialog(self, t.category)
        self.wait_window(dlg)
        if dlg.result and dlg.result != t.category:
            if self.manager.set_category(tid, dlg.result):
                self._log(tr("log.catchanged", t.filename, tr("cat." + dlg.result)))
                self._sync_tree()
            else:
                messagebox.showinfo(tr("msg.info"), tr("msg.cat_busy"))

    def _open_dir(self):
        if not self.models_dir:
            messagebox.showinfo(tr("msg.info"), tr("msg.no_dir"))
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(self.models_dir)
            else:
                messagebox.showinfo(tr("msg.info"), self.models_dir)
        except OSError as e:
            messagebox.showerror(tr("msg.err"), str(e))

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
            vals = (t["filename"], tr("cat." + t["category"]),
                    tr("st." + t["status"]), prog, speed, size,
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
        cnt = {k: 0 for k in _STATUS_KEYS}
        for t in snap:
            if t["status"] in cnt:
                cnt[t["status"]] += 1
        tot_bytes = sum(max(t["total"], t["downloaded"]) for t in snap)
        done_bytes = sum(t["downloaded"] for t in snap)
        gs = sum(t["speed"] for t in snap if t["status"] == "downloading")
        pct = int(done_bytes * 100 / tot_bytes) if tot_bytes else 0
        parts = [tr("count.total", len(snap))]
        for key, stat in (("count.done", "done"), ("count.skipped", "skipped"),
                          ("count.downloading", "downloading"),
                          ("count.pending", "pending"), ("count.paused", "paused"),
                          ("count.failed", "failed")):
            if cnt[stat]:
                parts.append(tr(key, cnt[stat]))
        self.stat_label.config(text="   ".join(parts) if snap else tr("st.ready"))
        self.gspeed_label.config(text=(tr("bar.speed", _human(gs))) if gs else "")
        self.gprog["value"] = pct
        self.gprog_label.config(text=tr("bar.prog", pct) if snap else "")

    # ------------------------------------------------------------- 其它
    def _save_opts(self):
        s = self.settings
        s["workers"] = int(self.workers_var.get() or 4)
        s["skip_existing"] = bool(self.skip_var.get())
        s["auto_mirror"] = bool(self.mirror_var.get())
        save_settings(s)

    def _log(self, msg):
        line = time.strftime("[%H:%M:%S] ") + msg
        self._log_lines.append(line)
        if len(self._log_lines) > 600:
            del self._log_lines[:len(self._log_lines) - 400]
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > 600:
            self.log.delete("1.0", "%d.0" % (lines - 400))
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_close(self):
        if self.manager.has_active():
            if not messagebox.askyesno(tr("msg.exit_title"), tr("msg.exit_body")):
                return
        self.manager.stop()
        self._save_opts()
        self.destroy()


def run():
    App().mainloop()
    return 0
