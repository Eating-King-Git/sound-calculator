"""Audio failure tests use a fake mixer and never require a sound device."""

import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from audio import SoundPlayer
from tools.create_sounds import AMPLITUDE, SAMPLE_RATE, TONES, create_sounds


class FakeChannel:
    def __init__(self):
        self.busy = True
        self.stops = 0

    def get_busy(self):
        return self.busy

    def stop(self):
        self.busy = False
        self.stops += 1


class FakeSound:
    def __init__(self, mixer, path):
        self.mixer = mixer
        self.path = path
        self.plays = 0
        self.channels = []

    def play(self):
        if self.mixer.fail_play:
            raise RuntimeError("device disappeared")
        self.plays += 1
        channel = FakeChannel()
        self.channels.append(channel)
        return channel

    def stop(self):
        for channel in self.channels:
            if channel.get_busy():
                channel.stop()


class FakeMixer:
    def __init__(self, initialized=False, fail_init=False, fail_load=False):
        self.initialized = initialized
        self.fail_init = fail_init
        self.fail_load = fail_load
        self.fail_play = False
        self.inits = 0
        self.quits = 0
        self.sounds = []

    def get_init(self):
        return (44100, -16, 1) if self.initialized else None

    def init(self, **kwargs):
        self.inits += 1
        if self.fail_init:
            raise RuntimeError("no audio device")
        self.initialized = True

    def Sound(self, path):
        if self.fail_load:
            raise RuntimeError("invalid wave")
        sound = FakeSound(self, path)
        self.sounds.append(sound)
        return sound

    def quit(self):
        self.quits += 1
        self.initialized = False


class AudioTests(unittest.TestCase):
    def player(self, mixer=None, **kwargs):
        mixer = mixer or FakeMixer()
        player = SoundPlayer(backend_loader=lambda: mixer, **kwargs)
        self.addCleanup(player.close)
        return player, mixer

    def test_disabled_start_does_not_import_or_initialize(self):
        with patch("audio.importlib.import_module") as loader:
            player = SoundPlayer(enabled=False)
            self.addCleanup(player.close)
            player.play("1")
            loader.assert_not_called()
            self.assertFalse(player.available)
            self.assertFalse(player.enabled)

    def test_missing_dependency_is_silent(self):
        with patch("audio.importlib.import_module", side_effect=ImportError("pygame")):
            player = SoundPlayer()
            self.addCleanup(player.close)
            self.assertFalse(player.available)
            self.assertIn("静音", player.status)
            player.play("1")

    def test_no_device_is_silent(self):
        player, mixer = self.player(FakeMixer(fail_init=True))
        self.assertFalse(player.available)
        self.assertEqual(mixer.quits, 0)
        player.play("+")

    def test_missing_assets_are_silent_without_initializing_device(self):
        with tempfile.TemporaryDirectory() as temporary:
            player, mixer = self.player(assets_dir=Path(temporary))
            self.assertFalse(player.available)
            self.assertEqual(mixer.inits, 0)

    def test_bad_asset_releases_owned_mixer(self):
        player, mixer = self.player(FakeMixer(fail_load=True))
        self.assertFalse(player.available)
        self.assertEqual(mixer.quits, 1)
        player.close()
        self.assertEqual(mixer.quits, 1)

    def test_existing_mixer_is_not_closed_when_asset_load_fails(self):
        player, mixer = self.player(FakeMixer(initialized=True, fail_load=True))
        self.assertFalse(player.available)
        player.close()
        self.assertEqual(mixer.inits, 0)
        self.assertEqual(mixer.quits, 0)

    def test_paths_are_independent_of_working_directory(self):
        old = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                player, mixer = self.player()
                self.assertTrue(player.available)
                for sound in mixer.sounds:
                    self.assertEqual(
                        Path(sound.path).parent,
                        Path(__file__).resolve().parent / "assets" / "sounds",
                    )
            finally:
                os.chdir(old)

    def test_number_and_operator_sounds(self):
        player, mixer = self.player()
        player.play("1")
        player.play(".")
        player.play("+")
        self.assertEqual([sound.plays for sound in mixer.sounds], [2, 1])

    def test_toggle_silences_channels_and_reuses_backend(self):
        player, mixer = self.player()
        player.play("1")
        channel = mixer.sounds[0].channels[0]
        player.set_enabled(False)
        player.play("+")
        self.assertFalse(channel.busy)
        self.assertEqual([sound.plays for sound in mixer.sounds], [1, 0])
        player.set_enabled(True)
        player.play("+")
        self.assertEqual(mixer.inits, 1)
        self.assertEqual(mixer.sounds[1].plays, 1)

    def test_enabling_after_silent_start_initializes(self):
        player, mixer = self.player(enabled=False)
        self.assertEqual(mixer.inits, 0)
        player.set_enabled(True)
        self.assertTrue(player.available)
        self.assertEqual(mixer.inits, 1)

    def test_failed_backend_can_be_retried(self):
        mixer = FakeMixer(fail_init=True)
        player, _ = self.player(mixer)
        mixer.fail_init = False
        player.set_enabled(True)
        self.assertTrue(player.available)
        self.assertEqual(mixer.inits, 2)

    def test_play_failure_silently_releases_owned_backend(self):
        player, mixer = self.player()
        mixer.fail_play = True
        player.play("1")
        self.assertFalse(player.available)
        self.assertIn("静音", player.status)
        self.assertEqual(mixer.quits, 1)

    def test_close_does_not_quit_external_mixer(self):
        player, mixer = self.player(FakeMixer(initialized=True))
        player.play("1")
        channel = mixer.sounds[0].channels[0]
        player.close()
        player.close()
        self.assertEqual(channel.stops, 1)
        self.assertEqual(mixer.quits, 0)
        self.assertFalse(player.enabled)

    def test_close_is_idempotent_for_owned_mixer(self):
        player, mixer = self.player()
        player.close()
        player.close()
        self.assertEqual(mixer.quits, 1)
        self.assertFalse(player.available)

    def test_synthesis_is_repeatable_and_has_valid_wave_parameters(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            create_sounds(target)
            first = {name: (target / f"{name}.wav").read_bytes() for name in TONES}
            create_sounds(target)
            for name, (_, duration) in TONES.items():
                self.assertEqual(first[name], (target / f"{name}.wav").read_bytes())
                with wave.open(str(target / f"{name}.wav"), "rb") as sound:
                    self.assertEqual(sound.getnchannels(), 1)
                    self.assertEqual(sound.getsampwidth(), 2)
                    self.assertEqual(sound.getframerate(), SAMPLE_RATE)
                    count = sound.getnframes()
                    self.assertEqual(count, round(SAMPLE_RATE * duration))
                    samples = struct.unpack(f"<{count}h", sound.readframes(count))
                    self.assertEqual(samples[0], 0)
                    self.assertEqual(samples[-1], 0)
                    self.assertLessEqual(max(map(abs, samples)), round(32767 * AMPLITUDE))
                    self.assertGreater(max(map(abs, samples)), 0)


if __name__ == "__main__":
    unittest.main()
