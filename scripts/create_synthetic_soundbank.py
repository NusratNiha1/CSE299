import argparse
from pathlib import Path
import numpy as np
import soundfile as sf

"""
Creates a synthetic household-style soundbank for Scaper when you have no real recordings yet.
Backgrounds: steady low-frequency hum + broadband noise + optional slow amplitude modulation.
Events: short beeps, clicks, chimes, whoosh-like noise bursts.
All audio written as 16-bit PCM WAV at target sample rate.
"""

SR = 16000

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def normalize(x):
    m = np.max(np.abs(x))
    if m < 1e-9:
        return x
    return x / m * 0.9


def gen_background(duration_s: float, hum_freq=120.0):
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    hum = 0.3 * np.sin(2 * np.pi * hum_freq * t)
    # slow amplitude modulation
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t)
    noise = 0.05 * np.random.randn(len(t))
    return normalize((hum * mod) + noise)


def gen_beep(duration_s: float, freq=1000.0):
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    env = np.minimum(1.0, t / 0.01) * np.exp(-3 * t / duration_s)
    sig = np.sin(2 * np.pi * freq * t) * env
    return normalize(sig)


def gen_click():
    length = int(0.02 * SR)
    x = np.zeros(length)
    x[0] = 1.0
    noise_tail = 0.3 * np.random.randn(length)
    x = normalize(x + noise_tail)
    return x


def gen_chime(duration_s: float):
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    freqs = [523.25, 659.25, 783.99]  # C major triad style
    sig = sum(np.sin(2 * np.pi * f * t) * np.exp(-3 * t / duration_s) for f in freqs)
    return normalize(sig)


def gen_whoosh(duration_s: float):
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    noise = np.random.randn(len(t))
    # high-pass effect using simple diff
    hp = np.concatenate([[0], np.diff(noise)])
    env = np.sin(np.pi * t / duration_s)  # fade in/out
    return normalize(hp * env)


def write_wav(path: Path, data: np.ndarray):
    sf.write(str(path), data.astype(np.float32), SR, subtype="PCM_16")


def build_soundbank(root: Path, n_backgrounds: int, bg_duration: float, n_variants: int):
    bg_root = root / 'backgrounds'
    bg_label_dir = bg_root / 'ambience'
    evt_root = root / 'events'
    ensure_dir(bg_label_dir)
    # Event label folders
    labels = ['beep', 'click', 'chime', 'whoosh']
    for lbl in labels:
        ensure_dir(evt_root / lbl)

    # Backgrounds
    for i in range(n_backgrounds):
        g = gen_background(bg_duration, hum_freq=80 + 40 * np.random.rand())
        write_wav(bg_label_dir / f'bg_{i:03d}.wav', g)

    # Events
    for i in range(n_variants):
        write_wav(evt_root / 'beep' / f'beep_{i:03d}.wav', gen_beep(0.4 + 0.2 * np.random.rand(), freq=600 + 800 * np.random.rand()))
        write_wav(evt_root / 'click' / f'click_{i:03d}.wav', gen_click())
        write_wav(evt_root / 'chime' / f'chime_{i:03d}.wav', gen_chime(0.8 + 0.4 * np.random.rand()))
        write_wav(evt_root / 'whoosh' / f'whoosh_{i:03d}.wav', gen_whoosh(0.5 + 0.5 * np.random.rand()))


def main():
    ap = argparse.ArgumentParser(description='Create synthetic household-like soundbank for Scaper')
    ap.add_argument('--root', type=str, default='Soundbanks', help='Root folder to create backgrounds/events')
    ap.add_argument('--backgrounds', type=int, default=10, help='Number of background ambience files')
    ap.add_argument('--bg_duration', type=float, default=30.0, help='Duration in seconds for each background file')
    ap.add_argument('--variants', type=int, default=25, help='Number of variants per event label')
    args = ap.parse_args()

    root = Path(args.root)
    build_soundbank(root, args.backgrounds, args.bg_duration, args.variants)
    print(f"Synthetic soundbank created under {root}")

if __name__ == '__main__':
    main()
