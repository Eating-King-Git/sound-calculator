"""Optional, fail-soft button sounds; calculation never depends on audio.

``enabled`` is the user's preference. ``available`` records whether both
sound files were loaded. An unavailable device leaves the app usable silently.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any, Callable


def _load_mixer() -> Any:
    # Import only after the user enables sound. The calculator also runs when
    # pygame is absent; no import is attempted for --mute startup.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    return importlib.import_module("pygame").mixer


class SoundPlayer:
    """Load local tones, degrade to silence on failure, and own only our mixer.

    ``backend_loader`` and ``assets_dir`` allow device-independent tests. A
    backend follows pygame.mixer's get_init/init/Sound/quit interface.
    """

    def __init__(
        self,
        enabled: bool = True,
        *,
        backend_loader: Callable[[], Any] | None = None,
        assets_dir: str | Path | None = None,
    ) -> None:
        self.enabled = False
        self.available = False
        self.status = "已静音"
        self._loader = backend_loader or _load_mixer
        self._assets = (
            Path(assets_dir).resolve()
            if assets_dir is not None
            else Path(__file__).resolve().parent / "assets" / "sounds"
        )
        self._mixer: Any = None
        self._owns_mixer = False
        self._sounds: dict[str, Any] = {}
        self.set_enabled(enabled)

    def _stop_sounds(self) -> None:
        # Stop only our Sound objects. A saved Channel handle can be reused by
        # another sound after ours ends, so stopping that handle is unsafe.
        for sound in self._sounds.values():
            try:
                sound.stop()
            except Exception:
                pass

    def _release_backend(self) -> None:
        self._stop_sounds()
        self._sounds.clear()
        if self._mixer is not None and self._owns_mixer:
            try:
                self._mixer.quit()
            except Exception:
                pass
        self._mixer = None
        self._owns_mixer = False
        self.available = False

    def _initialize(self) -> None:
        self._release_backend()
        try:
            paths = {
                name: self._assets / f"{name}.wav"
                for name in ("number", "operator")
            }
            if not all(path.is_file() for path in paths.values()):
                raise FileNotFoundError("Button sound files are missing")
            self._mixer = self._loader()
            if not self._mixer.get_init():
                # Own a successful initialization; if init itself fails there
                # is no mixer initialized by this object to shut down.
                self._mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
                self._owns_mixer = True
            self._sounds = {
                name: self._mixer.Sound(str(path)) for name, path in paths.items()
            }
            self.available = True
            self.status = "音效已开启"
        except Exception:
            self._release_backend()
            self.status = "音效不可用，已静音"

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self._stop_sounds()
            self.status = "已静音"
        elif not self.available:
            self._initialize()
        else:
            self.status = "音效已开启"

    def play(self, key: str) -> None:
        if not self.enabled or not self.available:
            return
        try:
            name = "number" if len(key) == 1 and key in "0123456789." else "operator"
            self._sounds[name].play()
        except Exception:
            self._release_backend()
            self.status = "音效不可用，已静音"

    def close(self) -> None:
        """Idempotent cleanup; an externally initialized mixer stays alive."""
        self._release_backend()
        self.enabled = False
        self.status = "音效已关闭"
