"""Tkinter desktop calculator. Run with --mute to disable audio at startup."""

from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk

from audio import SoundPlayer
from calculator_core import CalculatorModel


class Calculator:
    """Keep widgets separate from calculation and optional audio backends."""

    def __init__(self, root: tk.Tk, *, sound=None, model=None) -> None:
        self.root = root
        self.model = model if model is not None else CalculatorModel()
        self.sound = sound if sound is not None else SoundPlayer()
        self.closed = False
        root.title("音效计算器 · Sound Calculator")
        root.geometry("420x740")
        root.minsize(380, 700)
        root.configure(bg="#f3f5f9")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<KeyPress>", self.on_key)

        self.display_var = tk.StringVar(root, "0")
        self.expression_var = tk.StringVar(root, "开始计算")
        self.error_var = tk.StringVar(root)
        self.audio_var = tk.StringVar(root)
        self.sound_enabled = tk.BooleanVar(root, self.sound.enabled)

        header = tk.Frame(root, bg="#f3f5f9")
        header.pack(fill="x", padx=22, pady=(20, 12))
        tk.Label(header, text="音效计算器", bg="#f3f5f9", fg="#17243d",
                 font=("Microsoft YaHei UI", 18, "bold")).pack(side="left")
        self.mute_button = ttk.Checkbutton(header, text="音效", variable=self.sound_enabled,
                                          command=self.toggle_sound)
        self.mute_button.pack(side="right")

        panel = tk.Frame(root, bg="#17243d", padx=16, pady=12)
        panel.pack(fill="x", padx=20)
        tk.Label(panel, textvariable=self.expression_var, anchor="e", wraplength=348,
                 bg="#17243d", fg="#a9bad4", font=("Segoe UI", 11)).pack(fill="x")
        self.display_label = tk.Label(panel, textvariable=self.display_var, anchor="e",
                                      bg="#17243d", fg="white", font=("Segoe UI", 30, "bold"))
        self.display_label.pack(fill="x", pady=(4, 0))
        tk.Label(panel, textvariable=self.error_var, anchor="e", wraplength=348,
                 bg="#17243d", fg="#ffbaad", font=("Microsoft YaHei UI", 9)).pack(fill="x")

        keypad = tk.Frame(root, bg="#f3f5f9")
        keypad.pack(fill="both", expand=True, padx=17, pady=(12, 8))
        for column in range(4):
            keypad.columnconfigure(column, weight=1, uniform="key")
        layout = [
            [("C", "C"), ("⌫", "Backspace"), ("%", "%"), ("√", "√")],
            [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "/")],
            [("4", "4"), ("5", "5"), ("6", "6"), ("×", "*")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("−", "-")],
            [("±", "±"), ("0", "0"), (".", "."), ("+", "+")],
        ]
        self.buttons = {}
        for row, cells in enumerate(layout):
            keypad.rowconfigure(row, weight=1)
            for column, (label, key) in enumerate(cells):
                operator = key in {"+", "-", "*", "/", "%", "√", "±"}
                button = tk.Button(
                    keypad, text=label, command=lambda k=key: self.press(k),
                    font=("Segoe UI", 17), bg="#e4eafa" if operator else "white",
                    fg="#244d9c" if operator else "#17243d", activebackground="#cedaf0",
                    relief="flat", borderwidth=0, cursor="hand2", takefocus=False,
                )
                button.grid(row=row, column=column, sticky="nsew", padx=3, pady=3)
                self.buttons[key] = button
        keypad.rowconfigure(5, weight=1)
        equals = tk.Button(keypad, text="=", command=lambda: self.press("="),
                           font=("Segoe UI", 20, "bold"), bg="#315fd2", fg="white",
                           activebackground="#244ba9", activeforeground="white",
                           relief="flat", borderwidth=0, cursor="hand2", takefocus=False)
        equals.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=3, pady=3)
        self.buttons["="] = equals

        bottom = tk.Frame(root, bg="#f3f5f9")
        bottom.pack(fill="x", padx=22, pady=(0, 16))
        tk.Label(bottom, text="最近计算 · 仅本次会话", anchor="w", bg="#f3f5f9",
                 fg="#54647d", font=("Microsoft YaHei UI", 9)).pack(fill="x")
        self.history_box = tk.Listbox(bottom, height=3, bg="#f3f5f9", fg="#334662",
                                      font=("Consolas", 10), relief="flat", borderwidth=0,
                                      highlightthickness=0, takefocus=False)
        self.history_box.pack(fill="x", pady=(3, 6))
        tk.Label(bottom, text="先乘除，后加减 · % 将当前数除以 100", anchor="w",
                 bg="#f3f5f9", fg="#64748b", font=("Microsoft YaHei UI", 9)).pack(fill="x")
        tk.Label(bottom, textvariable=self.audio_var, anchor="w", bg="#f3f5f9",
                 fg="#64748b", font=("Microsoft YaHei UI", 9)).pack(fill="x")
        self.refresh()
        root.after_idle(root.focus_set)

    def press(self, key: str) -> None:
        if self.closed:
            return
        self.model.press(key)
        self.sound.play(key)
        self.refresh()
        self.root.focus_set()

    def refresh(self) -> None:
        self.display_var.set(self.model.display)
        expression = self.model.expression or "开始计算"
        # The complete records remain in the scrollable history; bound this hint.
        self.expression_var.set(expression if len(expression) <= 56 else "…" + expression[-55:])
        self.error_var.set(self.model.error or "")
        self.display_label.configure(font=("Segoe UI", 30 if len(self.model.display) <= 16 else 17, "bold"))
        self.audio_var.set(self.sound.status)
        self.history_box.delete(0, tk.END)
        for record in self.model.history:
            self.history_box.insert(tk.END, record)
        self.history_box.yview_moveto(1.0)

    def toggle_sound(self) -> None:
        self.sound.set_enabled(self.sound_enabled.get())
        self.refresh()
        self.root.focus_set()

    def on_key(self, event):
        if self.closed:
            return None
        special = {"Return": "=", "KP_Enter": "=", "Escape": "C",
                   "Delete": "C", "BackSpace": "Backspace", "F9": "±"}
        key = special.get(event.keysym)
        char = event.char
        if key is None and char and char in "0123456789.+-*/=%":
            key = char
        elif key is None and char in {"c", "C"}:
            key = "C"
        elif key is None and char in {"r", "R"}:
            key = "√"
        if key is not None:
            self.press(key)
            return "break"
        return None

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.sound.close()
            self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mute", action="store_true", help="start without loading audio")
    args = parser.parse_args()
    root = tk.Tk()
    app = None
    sound = SoundPlayer(enabled=not args.mute)
    try:
        app = Calculator(root, sound=sound)
        root.mainloop()
    finally:
        if app is not None:
            app.close()
        else:
            sound.close()
            root.destroy()


if __name__ == "__main__":
    main()
