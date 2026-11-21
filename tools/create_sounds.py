"""Rebuild the project's two quiet synthetic button tones using only stdlib."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import struct
import wave


SAMPLE_RATE = 44100
AMPLITUDE = 0.12
TONES = {"number": (880.0, 0.08), "operator": (520.0, 0.10)}


def write_tone(path: Path, frequency: float, duration: float) -> None:
    """Write a mono 16-bit sine tone with a smooth zero-ended envelope."""
    if not 0 < frequency < SAMPLE_RATE / 2 or not 0 < duration <= 1:
        raise ValueError("Expected an audible frequency and duration in (0, 1]")
    count = max(2, round(SAMPLE_RATE * duration))
    frames = bytearray()
    for index in range(count):
        envelope = math.sin(math.pi * index / (count - 1)) ** 2
        sample = round(
            32767 * AMPLITUDE * envelope
            * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
        )
        frames.extend(struct.pack("<h", sample))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)


def create_sounds(output_dir: Path) -> None:
    for name, (frequency, duration) in TONES.items():
        write_tone(Path(output_dir) / f"{name}.wav", frequency, duration)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path(__file__).resolve().parents[1] / "assets" / "sounds",
    )
    args = parser.parse_args()
    create_sounds(args.output_dir)
    print(f"Generated number.wav and operator.wav in {args.output_dir}")


if __name__ == "__main__":
    main()
