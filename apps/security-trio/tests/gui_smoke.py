"""Real Tk widget acceptance smoke test. Run under xvfb-run on Linux."""
from __future__ import annotations
import os
import subprocess
import time
import tkinter
import sys
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tkinter import messagebox, ttk
from unittest.mock import patch
import app


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def find_button(root, label):
    for child in descendants(root):
        if isinstance(child, ttk.Button) and child.cget("text") == label:
            return child
    raise AssertionError(f"Missing button {label}")


def smoke(root):
    root.update()
    base = Path(__file__).parent.parent / "docs"
    base.mkdir(exist_ok=True)
    for mode, name in (("secret", "Secret Scout"), ("log", "Log Lantern"), ("file", "File Inspector")):
        find_button(root, name).invoke()
        find_button(root, "サンプルで試す").invoke()
        root.update()
        find_button(root, "検査を開始").invoke()
        ready = False
        for _ in range(400):
            root.update()
            time.sleep(0.015)
            # A successful scan fills the result Treeview; a failed scan returns its start button.
            trees = [c for c in descendants(root) if isinstance(c, ttk.Treeview)]
            result_tree = next(t for t in trees if "severity" in t["columns"])
            if result_tree.get_children():
                ready = True
                break
        assert ready, f"No findings in GUI for {mode}"
        if mode == "file":
            hash_tree = next(t for t in trees if "digest" in t["columns"])
            assert len(hash_tree.get_children()) >= 3
        if mode == "secret":
            first = result_tree.item(result_tree.get_children()[0], "values")
            assert not any("Zx7" in str(x) for x in first)
        root.update()
        time.sleep(0.15)
        if os.name != "nt" and shutil.which("scrot"):
            subprocess.run(["scrot", "-o", str(base / f"preview-{mode}.png")], check=True)
        print(f"GUI PASS {mode}: {len(result_tree.get_children())} findings")
    root.destroy()


if __name__ == "__main__":
    with patch.object(tkinter.Tk, "mainloop", new=smoke), patch.object(messagebox, "showinfo", return_value=None), patch.object(messagebox, "showerror", return_value=None):
        app.run_gui("secret")
