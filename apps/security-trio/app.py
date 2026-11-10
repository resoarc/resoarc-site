"""Desktop GUI and headless CLI for the three ResoArc Security Trio tools.

Python 3.10+; standard library only. No telemetry and no network access.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import secrets
import sys
import tempfile
import threading
import zipfile
from collections import Counter
from pathlib import Path
from typing import Callable

from common import SEVERITY_ORDER, ScanResult, VERSION, export_csv, export_json, safe_name, output_overwrites_input
import file_inspector
import log_lantern
import secret_scout

TOOLS = {
    "secret": ("Secret Scout", "公開する前に、秘密情報の混入を点検", "テキスト・設定ファイル・ZIPを確認", secret_scout.scan),
    "log": ("Log Lantern", "アクセスログから気になる動きを発見", "Apache / Nginx combined・IIS W3C形式", log_lantern.scan),
    "file": ("File Inspector", "添付ファイルを開く前に、静的な特徴を確認", "PDF・ショートカット・Office・実行形式など", file_inspector.scan),
}

BG = "#0d1422"
PANEL = "#162237"
PANEL2 = "#1b2b44"
BORDER = "#30445f"
TEXT = "#e9f2ff"
MUTED = "#9db0c9"
ACCENT = "#54dac1"
ACCENT_HOVER = "#78ead9"
HIGH = "#fc797f"
MEDIUM = "#eec37b"
LOW = "#9dd0ff"
FONT = "Yu Gothic UI" if os.name == "nt" else "Noto Sans CJK JP"


def run_cli(mode: str, paths: list[str], output: str | None, fmt: str) -> int:
    _, _, _, engine = TOOLS[mode]
    if output and output_overwrites_input(output, paths):
        print("Error: the report path points to an input file; no scan target was overwritten.", file=sys.stderr)
        return 2
    result = engine(paths)
    if output:
        (export_csv if fmt == "csv" else export_json)(output, result)
        print(f"{result.app}: {result.scanned} files; {len(result.findings)} findings; {len(result.errors)} errors")
    else:
        print(json.dumps(result.export_data(), ensure_ascii=False, indent=2))
    if (result.truncated or result.metrics.get("cancelled") or result.errors or result.skipped
            or result.metrics.get("unparsed_lines", 0)):
        # Partial analysis is never a success, even when some files were processed.
        return 2
    if any(f.severity in ("高", "中") for f in result.findings):
        return 1
    return 0


def build_samples(mode: str, root: Path) -> list[str]:
    """All samples are locally generated, inert mock files using nonreal credentials."""
    target = root / mode
    target.mkdir(parents=True, exist_ok=True)
    if mode == "secret":
        value = secrets.token_urlsafe(24)
        (target / "demo.env").write_text("# ResoArc synthetic demonstration only\nDATABASE_PASSWORD=" + value + "\n", encoding="utf-8")
        with zipfile.ZipFile(target / "demo.zip", "w") as z:
            z.writestr("settings/config.yaml", "client_secret: " + secrets.token_urlsafe(32) + "\n")
        return [str(target / "demo.env"), str(target / "demo.zip")]
    if mode == "log":
        lines = []
        for i in range(90):
            resource = "/.env" if i < 50 else "/ordinary-page"
            status = 404 if i < 50 else (403 if i < 70 else 200)
            lines.append(f'198.51.100.34 - - [08/Nov/2026:01:03:{i % 60:02d} +0900] "GET {resource}?tracking=PRIVATE_DEMO HTTP/1.1" {status} 255 "-" "ResoArcSample"')
        (target / "access.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return [str(target / "access.log")]
    header = bytearray(160)
    header[0:2] = b"MZ"
    header[0x3c:0x40] = (128).to_bytes(4, "little")
    header[128:132] = b"PE\0\0"
    (target / "invoice.pdf.exe").write_bytes(header)
    (target / "disguised.pdf").write_bytes(bytes(header))
    (target / "sample.pdf").write_bytes(b"%PDF-1.4\n1 0 obj << /OpenAction /JavaScript >> endobj\n%%EOF")
    (target / "shortcut.lnk").write_bytes(file_inspector.LNK_HEADER + b"\x00" * 50 + "powershell".encode("utf-16le"))
    return [str(p) for p in target.iterdir() if p.is_file()]


def run_gui(mode: str):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        root = TkinterDnD.Tk()
        has_dnd = True
    except ImportError:
        root = tk.Tk()
        has_dnd = False

    class SecurityApp:
        def __init__(self):
            self.root = root
            self.mode = mode
            self.paths: list[str] = []
            self.result: ScanResult | None = None
            self.cancel = threading.Event()
            self.messages: queue.Queue = queue.Queue()
            self.worker: threading.Thread | None = None
            self.sample_dir = tempfile.TemporaryDirectory(prefix="resoarc-security-samples-")
            self.root.title("ResoArc Security Trio  |  開発プレビュー")
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            # Compact desktops (VNC/low resolution) must not clip the file controls.
            self.compact = sw < 900 or sh < 640
            self.root.geometry(f"{min(1180, max(540, sw - 20))}x{min(850, max(380, sh - 70))}")
            self.root.minsize(540 if self.compact else 900, 370 if self.compact else 635)
            self.compact_body = None
            self.root.configure(bg=BG)
            self._style()
            self._build()
            self._set_mode(mode)
            self.root.bind("<Control-o>", lambda _: self.add_files())
            self.root.bind("<Control-r>", lambda _: self.start())
            self.root.bind("<Control-s>", lambda _: self.export("json"))
            self.root.bind("<Control-f>", lambda _: self.search_entry.focus_set())
            self.root.bind("<Delete>", lambda _: self.remove_selection())
            self.root.protocol("WM_DELETE_WINDOW", self.close)
            self.root.after(120, self.poll)
            if has_dnd:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind("<<Drop>>", self._drop)

        def _style(self):
            s = ttk.Style(self.root)
            s.theme_use("clam")
            s.configure("Root.TFrame", background=BG)
            s.configure("Panel.TFrame", background=PANEL)
            s.configure("TFrame", background=BG)
            s.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))
            s.configure("Secondary.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))
            s.configure("Card.TLabel", background=PANEL, foreground=TEXT, font=(FONT, 10))
            s.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED, font=(FONT, 9))
            s.configure("Metric.TLabel", background=PANEL, foreground=ACCENT, font=(FONT, 22, "bold"))
            s.configure("Hero.TLabel", background=BG, foreground=TEXT, font=(FONT, 22, "bold"))
            s.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 11))
            s.configure("Primary.TButton", background=ACCENT, foreground="#09252c", font=(FONT, 10, "bold"), padding=(15, 10), borderwidth=0)
            s.map("Primary.TButton", background=[("disabled", BORDER), ("active", ACCENT_HOVER)])
            s.configure("Secondary.TButton", background=PANEL2, foreground=TEXT, font=(FONT, 10), padding=(10, 8), borderwidth=0)
            s.configure("Compact.TButton", background=PANEL2, foreground=TEXT, font=(FONT, 10), padding=(5, 7), borderwidth=0)
            s.map("Secondary.TButton", background=[("disabled", BORDER), ("active", "#29405f")])
            s.configure("Danger.TButton", background="#513044", foreground="#ffd9e0", font=(FONT, 10), padding=(12, 9), borderwidth=0)
            s.map("Danger.TButton", background=[("active", "#713e51")])
            s.configure("Mode.TButton", background=BG, foreground=MUTED, font=(FONT, 10, "bold"), padding=(12, 9), borderwidth=0)
            s.map("Mode.TButton", background=[("active", PANEL2)])
            s.configure("ActiveMode.TButton", background=PANEL2, foreground=ACCENT, font=(FONT, 10, "bold"), padding=(12, 9), borderwidth=0)
            s.configure("Results.Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, font=(FONT, 10), rowheight=33, borderwidth=0)
            s.map("Results.Treeview", background=[("selected", "#315575")], foreground=[("selected", "#ffffff")])
            s.configure("Results.Treeview.Heading", background=PANEL2, foreground=MUTED, relief="flat", font=(FONT, 9, "bold"), padding=(6, 10))
            s.map("Results.Treeview.Heading", background=[("active", BORDER)])
            s.configure("TNotebook", background=BG, borderwidth=0)
            s.configure("TNotebook.Tab", background=PANEL2, foreground=MUTED, font=(FONT, 10), padding=(12, 6))
            s.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
            s.configure("TProgressbar", background=ACCENT, troughcolor=PANEL2, borderwidth=0, thickness=4)

        def _build(self):
            header = ttk.Frame(root, style="Root.TFrame",
                               padding=(9, 6, 9, 3) if self.compact else (27, 12, 27, 5))
            header.pack(fill="x")
            line = ttk.Frame(header)
            if not self.compact:
                line.pack(fill="x")
                ttk.Label(line, text="RESOARC  /  SECURITY TOOLS", foreground=ACCENT,
                          font=(FONT, 10, "bold")).pack(side="left")
            if not self.compact:
                ttk.Label(line, text="●  オフライン  ·  読み取り専用  ·  外部送信なし",
                          style="Secondary.TLabel").pack(side="right")
            nav = ttk.Frame(header)
            nav.pack(fill="x", pady=(4, 2) if self.compact else (9, 5))
            self.mode_buttons = {}
            for slug, (name, _, _, _) in TOOLS.items():
                btn = ttk.Button(nav, text=name, style="Mode.TButton", command=lambda v=slug: self._set_mode(v))
                btn.pack(side="left", padx=(0, 8))
                self.mode_buttons[slug] = btn
            self.hero = ttk.Label(header, style="Hero.TLabel")
            if not self.compact:
                self.hero.pack(anchor="w", pady=(3, 1))
            self.subtitle = ttk.Label(header, style="Sub.TLabel")
            if not self.compact:
                self.subtitle.pack(anchor="w", pady=(0, 1))

            if self.compact:
                body = ttk.Notebook(root)
                body.pack(fill="both", expand=True, padx=8, pady=(2, 2))
                side = ttk.Frame(body, style="Panel.TFrame", padding=7)
                main = ttk.Frame(body, style="Root.TFrame", padding=3)
                body.add(side, text="1. 検査するファイル")
                body.add(main, text="2. 検査と結果")
                self.compact_body = body
            else:
                body = ttk.Panedwindow(root, orient="horizontal")
                body.pack(fill="both", expand=True, padx=26, pady=(5, 4))
                side = ttk.Frame(body, style="Panel.TFrame", padding=12)
                body.add(side, weight=1)
                main = ttk.Frame(body, style="Root.TFrame")
                body.add(main, weight=4)

            ttk.Label(side, text="検査するファイル", background=PANEL, foreground=TEXT,
                      font=(FONT, 12, "bold")).pack(anchor="w", pady=(3, 2))
            ttk.Label(side, text="ファイルやフォルダを追加", style="CardMuted.TLabel").pack(anchor="w", pady=(0, 7))
            choice = ttk.Frame(side, style="Panel.TFrame")
            choice.pack(fill="x", pady=(0, 7))
            ttk.Button(choice, text="＋ ファイルを追加", style="Compact.TButton", command=self.add_files).pack(fill="x", pady=(0, 3))
            ttk.Button(choice, text="＋ フォルダを追加", style="Compact.TButton", command=self.add_folder).pack(fill="x")
            self.pathbox = tk.Listbox(side, bg=PANEL2, fg=TEXT, selectbackground="#315575",
                                     selectforeground=TEXT, relief="flat", highlightthickness=1,
                                     highlightbackground=BORDER, highlightcolor=ACCENT,
                                     font=(FONT, 10), activestyle="none", selectmode="extended")
            self.pathbox.pack(fill="both", expand=True, pady=(0, 7))
            remove_btn = ttk.Button(side, text="選択を削除", style="Secondary.TButton", command=self.remove_selection)
            remove_btn.pack(fill="x", pady=(0, 5))
            sample_btn = ttk.Button(side, text="サンプルで試す", style="Secondary.TButton", command=self.load_sample)
            sample_btn.pack(fill="x", pady=(0, 5))
            self.dnd_hint = ttk.Label(side, text="この画面へドロップして追加できます" if has_dnd else "Ctrl+O でもファイルを追加できます",
                                      style="CardMuted.TLabel", wraplength=250)
            self.dnd_hint.pack(anchor="w", pady=(4, 4))
            note = tk.Label(side, text="点検結果は安全を保証しません。",
                            bg=PANEL, fg=MUTED, justify="left", anchor="w", wraplength=245,
                            font=(FONT, 9))
            note.pack(fill="x", pady=(0, 4))
            # Bottom actions remain visible even when the window height is compact.
            self.pathbox.pack_forget()
            remove_btn.pack_forget()
            sample_btn.pack_forget()
            self.dnd_hint.pack_forget()
            note.pack_forget()
            note.pack(side="bottom", fill="x", pady=(1, 3))
            self.dnd_hint.pack(side="bottom", anchor="w", pady=(0, 3))
            sample_btn.pack(side="bottom", fill="x", pady=(0, 5))
            remove_btn.pack(side="bottom", fill="x", pady=(0, 5))
            self.pathbox.pack(side="top", fill="both", expand=True, pady=(0, 7))

            controls = ttk.Frame(main, style="Root.TFrame")
            controls.pack(fill="x", pady=(0, 6))
            self.scan_btn = ttk.Button(controls, text="検査を開始", style="Primary.TButton", command=self.start)
            self.scan_btn.pack(side="left", padx=(0, 8))
            self.cancel_btn = ttk.Button(controls, text="停止", style="Danger.TButton", command=self.stop)
            self.cancel_btn.pack(side="left", padx=(0, 8))
            self.cancel_btn.configure(state="disabled")
            ttk.Button(controls, text="JSON保存", style="Secondary.TButton", command=lambda: self.export("json")).pack(side="right", padx=(6, 0))
            ttk.Button(controls, text="CSV保存", style="Secondary.TButton", command=lambda: self.export("csv")).pack(side="right")
            self.progress = ttk.Progressbar(main, mode="determinate", value=0)
            if not self.compact:
                self.progress.pack(fill="x", pady=(0, 7))
            # Compact mode uses the visible status text to communicate progress.
            self.cards = ttk.Frame(main, style="Root.TFrame")
            if not self.compact:
                self.cards.pack(fill="x", pady=(0, 7))
            self.metric_labels = {}
            for i, (slug, title) in enumerate((('scanned', '検査済み'), ('findings', '検出事項'), ('high', '高リスク'), ('errors', '読取エラー'))):
                block = ttk.Frame(self.cards, style="Panel.TFrame", padding=9)
                block.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 6, 0))
                ttk.Label(block, text=title, style="CardMuted.TLabel").pack(anchor="w")
                label = ttk.Label(block, text="0", style="Metric.TLabel")
                label.pack(anchor="w", pady=(2, 0))
                self.metric_labels[slug] = label

            tabs = ttk.Notebook(main)
            tabs.pack(fill="both", expand=True)
            result_page = ttk.Frame(tabs, style="Panel.TFrame", padding=8)
            graph_page = ttk.Frame(tabs, style="Panel.TFrame", padding=12)
            hash_page = ttk.Frame(tabs, style="Panel.TFrame", padding=8)
            tabs.add(result_page, text="検出結果")
            tabs.add(graph_page, text="傾向と補足")
            tabs.add(hash_page, text="ファイルハッシュ")

            filters = ttk.Frame(result_page, style="Panel.TFrame")
            filters.pack(fill="x", pady=(0, 1) if self.compact else (0, 6))
            ttk.Label(filters, text="重要度", style="CardMuted.TLabel").pack(side="left", padx=(0, 5))
            self.filter_var = tk.StringVar(value="すべて")
            severity_box = ttk.Combobox(filters, textvariable=self.filter_var, state="readonly",
                                        values=("すべて", "高", "中", "低", "情報"), width=6)
            severity_box.pack(side="left", padx=(0, 12))
            severity_box.bind("<<ComboboxSelected>>", lambda _: self._render_findings())
            ttk.Label(filters, text="絞り込み", style="CardMuted.TLabel").pack(side="left", padx=(0, 5))
            self.search_var = tk.StringVar()
            self.search_entry = ttk.Entry(filters, textvariable=self.search_var, width=20)
            self.search_entry.pack(side="left", fill="x", expand=True)
            self.search_entry.bind("<KeyRelease>", lambda _: self._render_findings())
            ttk.Button(filters, text="解除", style="Compact.TButton",
                       command=self.clear_filters).pack(side="left", padx=(6, 0))

            columns = ("severity", "rule", "target", "detail")
            self.tree = ttk.Treeview(result_page, columns=columns, show="headings", selectmode="browse", style="Results.Treeview")
            for key, title, width in (("severity", "重要度", 70), ("rule", "検出内容", 160), ("target", "対象", 135), ("detail", "説明", 245)):
                self.tree.heading(key, text=title)
                self.tree.column(key, width=width, minwidth=60, stretch=key == "detail", anchor="w")
            self.tree.tag_configure("高", foreground=HIGH)
            self.tree.tag_configure("中", foreground=MEDIUM)
            self.tree.tag_configure("低", foreground=LOW)
            self.tree.tag_configure("情報", foreground=MUTED)
            scrollbar = ttk.Scrollbar(result_page, orient="vertical", command=self.tree.yview)
            scroll_x = ttk.Scrollbar(result_page, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=scroll_x.set)
            scroll_x.pack(side="bottom", fill="x")
            self.tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            self.tree.bind("<<TreeviewSelect>>", self.show_detail)
            if self.compact:
                self.tree.bind("<Double-1>", self.show_detail_dialog)

            ttk.Label(graph_page, text="検査の傾向", background=PANEL, foreground=TEXT,
                      font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 8))
            self.graph = tk.Canvas(graph_page, bg=PANEL, highlightthickness=0,
                                   height=90 if self.compact else 190)
            self.graph.pack(fill="x", pady=(0, 10))
            self.summary = tk.Text(graph_page, height=5 if self.compact else 11, bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                                   font=(FONT, 10), wrap="word", relief="flat", padx=12, pady=12,
                                   highlightthickness=1, highlightbackground=BORDER)
            self.summary.pack(fill="both", expand=True)
            self.summary.configure(state="disabled")
            self.graph.bind("<Configure>", lambda _: self.update_graph())

            self.hash_tree = ttk.Treeview(hash_page, columns=("filename", "kind", "digest"),
                                          show="headings", style="Results.Treeview")
            for key, title, width in (("filename", "ファイル名", 200), ("kind", "実形式", 95), ("digest", "SHA-256", 450)):
                self.hash_tree.heading(key, text=title)
                self.hash_tree.column(key, width=width, stretch=key == "digest")
            self.hash_tree.pack(fill="both", expand=True)
            ttk.Button(hash_page, text="選択したSHA-256をコピー", style="Secondary.TButton", command=self.copy_digest).pack(anchor="e", pady=(10, 0))

            detail = ttk.Frame(main, style="Panel.TFrame", padding=(6, 3),
                               height=44 if self.compact else 70)
            detail.pack_propagate(False)
            detail.pack(fill="x", pady=(10, 0))
            self.detail_var = tk.StringVar(value="結果を選択すると、確認ポイントと対策を表示します。")
            ttk.Label(detail, textvariable=self.detail_var, style="Card.TLabel",
                      wraplength=530 if self.compact else 870,
                      justify="left").pack(anchor="w")
            self.status_var = tk.StringVar(value="準備完了。ファイルやフォルダを追加してください。")
            ttk.Label(header, textvariable=self.status_var, style="Secondary.TLabel",
                      padding=(1, 5, 1, 0)).pack(fill="x")
            # Reserve space for the selected finding details even in a compact window.
            tabs.pack_forget()
            detail.pack_forget()
            if not self.compact:
                detail.pack(side="bottom", fill="x", pady=(10, 0))
            tabs.pack(side="top", fill="both", expand=True)

        def _set_mode(self, new_mode):
            if self.worker and self.worker.is_alive():
                messagebox.showinfo("検査中", "検査完了または停止後に切り替えてください。")
                return
            self.mode = new_mode
            if self.compact_body is not None:
                self.compact_body.select(0)
            self.paths.clear()
            self.pathbox.delete(0, "end")
            self.result = None
            self.clear_filters()
            name, description, caption, _ = TOOLS[new_mode]
            self.hero.configure(text=name)
            self.subtitle.configure(text=description + "  ·  " + caption)
            for slug, button in self.mode_buttons.items():
                button.configure(style="ActiveMode.TButton" if slug == new_mode else "Mode.TButton")
            self._render()
            self.status_var.set("モードを切り替えました。検査対象を追加してください。")

        def _drop(self, event):
            try:
                self.add_paths(self.root.tk.splitlist(event.data))
            except (ValueError, RuntimeError):
                self.status_var.set("ドロップしたファイルを読み取れませんでした。")

        def add_paths(self, new_paths):
            if self.worker and self.worker.is_alive():
                return
            for raw in new_paths:
                p = Path(raw)
                if p.exists() and str(p) not in self.paths:
                    self.paths.append(str(p))
                    self.pathbox.insert("end", safe_name(p.name))
            self.status_var.set(f"選択済み: {len(self.paths)} 件。検査開始を押してください。")
            if self.compact_body is not None and self.paths:
                self.compact_body.select(1)

        def add_files(self):
            selected = filedialog.askopenfilenames(title="検査するファイルを選択")
            self.add_paths(selected)

        def add_folder(self):
            selected = filedialog.askdirectory(title="検査するフォルダを選択")
            if selected:
                self.add_paths([selected])

        def remove_selection(self):
            if self.worker and self.worker.is_alive():
                return
            for index in reversed(self.pathbox.curselection()):
                del self.paths[index]
                self.pathbox.delete(index)
            self.status_var.set(f"選択済み: {len(self.paths)} 件。")

        def load_sample(self):
            if self.worker and self.worker.is_alive():
                return
            paths = build_samples(self.mode, Path(self.sample_dir.name))
            self.add_paths(paths)
            messagebox.showinfo("試用サンプル", "無害な模擬データを追加しました。\n外部通信も不正なコードの実行も行いません。")

        def start(self):
            if self.worker and self.worker.is_alive():
                return
            if not self.paths:
                messagebox.showinfo("対象なし", "先にファイル・フォルダを追加してください。")
                return
            self.result = None
            self._render()
            self.cancel.clear()
            self.scan_btn.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
            self.progress.configure(mode="indeterminate")
            self.progress.start(14)
            self.status_var.set("検査中…")
            paths = list(self.paths)
            scan_func: Callable = TOOLS[self.mode][3]
            def task():
                try:
                    output = scan_func(paths, progress=lambda filename: self.messages.put(("progress", filename)), cancel=self.cancel)
                    self.messages.put(("result", output))
                except Exception as error:
                    self.messages.put(("error", type(error).__name__))
            self.worker = threading.Thread(target=task, daemon=True, name="resoarc-scan")
            self.worker.start()

        def stop(self):
            self.cancel.set()
            self.status_var.set("停止を要求しました。読み取り処理が終了するまで処理中です。")

        def poll(self):
            try:
                while True:
                    kind, payload = self.messages.get_nowait()
                    if kind == "progress":
                        self.status_var.set("検査中: " + payload)
                    elif kind == "result":
                        self.result = payload
                        self._complete()
                        incomplete = payload.truncated or payload.skipped or payload.errors or payload.metrics.get("unparsed_lines", 0)
                        state_label = "中断" if payload.metrics.get("cancelled") else ("一部未検査" if incomplete else "完了")
                        self.status_var.set(f"{state_label}: {payload.scanned} 件を検査、{len(payload.findings)} 件の検出事項、{len(payload.errors)} 件の読取エラー。")
                    elif kind == "error":
                        self._complete()
                        messagebox.showerror("処理エラー", "検査を完了できませんでした。エラー種別: " + payload)
            except queue.Empty:
                pass
            self.root.after(120, self.poll)

        def _complete(self):
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
            self.scan_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            self.worker = None
            self._render()

        def _render(self):
            for tree in (self.tree, self.hash_tree):
                tree.delete(*tree.get_children())
            result = self.result
            counts = Counter(f.severity for f in result.findings) if result else Counter()
            values = {
                "scanned": result.scanned if result else 0,
                "findings": len(result.findings) if result else 0,
                "high": counts["高"], "errors": len(result.errors) if result else 0,
            }
            for key, label in self.metric_labels.items():
                label.configure(text=str(values[key]))
            if result:
                self._render_findings()
                for record in result.metrics.get("files", []):
                    self.hash_tree.insert("", "end", values=(record["file"], record["detected_type"], record["sha256"]))
            self.detail_var.set("結果を選択すると、確認ポイントと対策を表示します。")
            self.update_graph()
            self._set_summary()

        def clear_filters(self):
            self.filter_var.set("すべて")
            self.search_var.set("")
            self._render_findings()

        def _render_findings(self):
            if not hasattr(self, "tree"):
                return
            self.tree.delete(*self.tree.get_children())
            if not self.result:
                return
            severity = self.filter_var.get()
            phrase = self.search_var.get().casefold().strip()
            items = sorted(enumerate(self.result.findings),
                           key=lambda pair: (SEVERITY_ORDER.get(pair[1].severity, 9), pair[0]))
            for n, f in items:
                if severity != "すべて" and f.severity != severity:
                    continue
                if phrase and not any(phrase in item.casefold()
                                      for item in (f.rule, f.target, f.detail, f.advice)):
                    continue
                self.tree.insert("", "end", iid=str(n), tags=(f.severity,),
                                 values=(f.severity, f.rule, f.target, f.detail))

        def _set_summary(self):
            result = self.result
            if not result:
                body = "検査結果の要約をここに表示します。\n\nSecret Scout は秘密の値をマスクします。\nLog Lantern はIPとURLのクエリを匿名化します。\nFile Inspector は対象を実行せず、ハッシュ値と特徴だけを読みます。"
            else:
                m = result.metrics
                body = f"検査済み {result.scanned} 件 / 対象外・一部除外 {result.skipped} 件\n"
                body += f"高 {sum(f.severity == '高' for f in result.findings)} 件、中 {sum(f.severity == '中' for f in result.findings)} 件、低 {sum(f.severity == '低' for f in result.findings)} 件\n\n"
                if self.mode == "log":
                    body += f"解析アクセス {m.get('requests', 0)} 件 / 解析できない行 {m.get('unparsed_lines', 0)} 件\n\n"
                    body += "アクセスの多いURL（クエリ除去済み）:\n"
                    body += "\n".join(f"  {x['requests']:>5}  {x['path']}" for x in m.get("popular_paths", [])[:8]) + "\n"
                if self.mode == "file":
                    body += "SHA-256は『ファイルハッシュ』タブで確認できます。\n"
                if self.mode == "secret":
                    body += "マッチした秘密情報の値は、画面にも出力ファイルにも記録しません。\n"
                if result.truncated or m.get("cancelled") or result.skipped or result.errors or m.get("unparsed_lines", 0):
                    body += "\n※ 一部未検査・中断・読取エラーがあります。検出ゼロでも完了とは判断できません。\n"
                if result.truncated:
                    body += "\n注意: 走査・検出件数・ログ行数の上限に達しています。入力を分けて再検査してください。\n"
                if result.errors:
                    body += "\n読取エラー・制限:\n" + "\n".join(" • " + e for e in result.errors[:10])
                body += "\n\n※ 検出がない場合も安全は保証できません。"
            self.summary.configure(state="normal")
            self.summary.delete("1.0", "end")
            self.summary.insert("1.0", body)
            self.summary.configure(state="disabled")

        def update_graph(self):
            if not hasattr(self, "graph"):
                return
            c = self.graph
            c.delete("all")
            result = self.result
            if not result:
                c.create_text(24, 35, text="検査後に重要度・ステータスの内訳を表示します。", anchor="nw", fill=MUTED, font=(FONT, 11))
                return
            if self.mode == "log":
                stats = result.metrics.get("status_codes", {})
                groups = [(str(k), int(v)) for k, v in sorted(stats.items(), key=lambda x: -x[1])[:6]]
            else:
                count = Counter(f.severity for f in result.findings)
                groups = [(label, count[label]) for label in ("高", "中", "低", "情報")]
            width = max(350, c.winfo_width())
            max_value = max((v for _, v in groups), default=1) or 1
            for i, (name, n) in enumerate(groups):
                y = 24 + i * 28
                c.create_text(18, y, text=name, anchor="w", fill=TEXT, font=(FONT, 10))
                barwidth = max(0, (width - 180) * n / max_value)
                color = HIGH if name == "高" else (MEDIUM if name == "中" else ACCENT)
                c.create_rectangle(115, y - 7, 115 + barwidth, y + 7, fill=color, outline="")
                c.create_text(width - 23, y, text=str(n), anchor="e", fill=TEXT, font=(FONT, 10, "bold"))

        def show_detail(self, _event=None):
            ids = self.tree.selection()
            if not ids or not self.result:
                return
            f = self.result.findings[int(ids[0])]
            line = f" / {f.line}行" if f.line else ""
            detail = f"[{f.severity}] {f.rule}  ·  {f.target}{line}\n{f.detail}"
            if f.advice:
                detail += "\n対策: " + f.advice
            self.detail_var.set(detail)
            if self.compact:
                self.status_var.set(f"選択: {f.rule}。詳細は行をダブルクリックしてください。")

        def show_detail_dialog(self, _event=None):
            if self.compact and self.tree.selection():
                self.show_detail()
                messagebox.showinfo("検査結果の詳細", self.detail_var.get())

        def copy_digest(self):
            selected = self.hash_tree.selection()
            if not selected:
                messagebox.showinfo("選択なし", "ハッシュ一覧からファイルを選択してください。")
                return
            digest = self.hash_tree.item(selected[0], "values")[2]
            self.root.clipboard_clear()
            self.root.clipboard_append(digest)
            self.status_var.set("SHA-256をクリップボードへコピーしました。")

        def export(self, fmt):
            if not self.result:
                messagebox.showinfo("保存する結果なし", "検査を完了してから保存してください。")
                return
            # Exports intentionally include all findings, not only the screen filter.
            default = "ResoArc_" + self.mode + "_report." + fmt
            path = filedialog.asksaveasfilename(title="検査レポートを保存", initialfile=default,
                                                defaultextension="." + fmt,
                                                filetypes=[("JSON", "*.json")] if fmt == "json" else [("CSV", "*.csv")])
            if not path:
                return
            if output_overwrites_input(path, self.paths):
                messagebox.showerror("保存先の安全確認", "検査対象ファイルをレポートで上書きできません。別の名前を指定してください。")
                return
            try:
                (export_json if fmt == "json" else export_csv)(path, self.result)
                self.status_var.set("レポートを保存しました: " + safe_name(Path(path).name))
            except OSError:
                messagebox.showerror("保存失敗", "ファイルを保存できません。出力先のアクセス権を確認してください。")

        def close(self):
            self.cancel.set()
            # Do not remove temporary sample files while a worker still reads them.
            # Process exit frees the temporary data; explicit cleanup is safe if idle.
            if not (self.worker and self.worker.is_alive()):
                try:
                    self.sample_dir.cleanup()
                except OSError:
                    pass
            self.root.destroy()

    SecurityApp()
    root.mainloop()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ResoArc Security Trio: offline, read-only inspection")
    parser.add_argument("paths", nargs="*", help="Files and directories to scan in headless mode")
    parser.add_argument("--mode", choices=TOOLS.keys(), default="secret")
    parser.add_argument("--output", help="Save headless report to this path")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args(argv)
    if args.paths:
        return run_cli(args.mode, args.paths, args.output, args.format)
    if args.output:
        parser.error("--output requires one or more input paths")
    run_gui(args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
