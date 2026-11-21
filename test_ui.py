"""Exercise real Tk widgets; require a display when REQUIRE_GUI=1."""

import os
from types import SimpleNamespace
import tkinter as tk
import unittest

from calculator import Calculator


class QuietSound:
    enabled = False
    available = False
    status = "音效关闭"

    def __init__(self):
        self.played = []
        self.closed = False

    def play(self, key):
        self.played.append(key)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.status = "音效开启" if enabled else "音效关闭"

    def close(self):
        self.closed = True


class CalculatorUITests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            if os.environ.get("REQUIRE_GUI") == "1":
                raise
            self.skipTest(f"Tk display unavailable: {exc}")
        self.root.withdraw()
        self.sound = QuietSound()
        self.app = Calculator(self.root, sound=self.sound)
        self.addCleanup(self.app.close)
        self.root.update_idletasks()

    def press_buttons(self, sequence):
        for key in sequence:
            self.app.buttons[key].invoke()

    def test_original_addition_regression_through_widgets(self):
        self.press_buttons("1+2=")
        self.assertEqual(self.app.display_var.get(), "3")
        self.assertEqual(self.app.history_box.size(), 1)

    def test_precedence_and_continuation(self):
        self.press_buttons("2+3*4=")
        self.assertEqual(self.app.display_var.get(), "14")
        self.press_buttons("/2=")
        self.assertEqual(self.app.display_var.get(), "7")

    def test_error_recovery_and_error_text(self):
        self.press_buttons("1/0=")
        self.assertTrue(self.app.error_var.get())
        self.press_buttons("7+2=")
        self.assertFalse(self.app.error_var.get())
        self.assertEqual(self.app.display_var.get(), "9")

    def test_empty_char_and_special_key_mapping(self):
        self.assertIsNone(self.app.on_key(SimpleNamespace(char="", keysym="F1")))
        self.assertEqual(self.app.display_var.get(), "0")
        for ch in "12":
            self.app.on_key(SimpleNamespace(char=ch, keysym=ch))
        self.app.on_key(SimpleNamespace(char="", keysym="BackSpace"))
        self.assertEqual(self.app.display_var.get(), "1")
        self.app.on_key(SimpleNamespace(char="", keysym="F9"))
        self.assertEqual(self.app.display_var.get(), "-1")
        self.app.on_key(SimpleNamespace(char="", keysym="Escape"))
        self.assertEqual(self.app.display_var.get(), "0")

    def test_return_square_root_and_percent(self):
        for ch in "81r":
            self.app.on_key(SimpleNamespace(char=ch, keysym=ch))
        self.app.on_key(SimpleNamespace(char="\r", keysym="Return"))
        self.assertEqual(self.app.display_var.get(), "9")
        self.press_buttons(["%", "="])
        self.assertEqual(self.app.display_var.get(), "0.09")

    def test_sound_switch_and_single_play_per_action(self):
        self.app.mute_button.invoke()
        self.assertTrue(self.sound.enabled)
        self.app.buttons["C"].invoke()
        self.assertEqual(self.sound.played, ["C"])
        self.assertEqual(self.app.audio_var.get(), "音效开启")

    def test_close_is_idempotent(self):
        self.app.close()
        self.app.close()
        self.assertTrue(self.sound.closed)
        self.assertTrue(self.app.closed)


if __name__ == "__main__":
    unittest.main()
