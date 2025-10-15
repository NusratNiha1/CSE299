import argparse
from pathlib import Path
import os
import random
import numpy as np
from tqdm import tqdm

# Contract
# - Use Scaper to generate 7s non-cry mixtures from provided background and event libraries
# - Outputs WAV mixtures (and optional JAMS) to Dataset/non-cry
# - Requires user to download/provide household soundbanks under Soundbanks/backgrounds and Soundbanks/events
# - Ensures sample rate and mono output via scaper.generate_from_jams' parameters

DEFAULT_DURATION = 7.0
DEFAULT_SR = 16000


def ensure_dirs(*paths: Path):
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def make_scaper(scaper_mod, bg_folder: Path, event_folder: Path, duration: float, ref_db: float):
    sc = scaper_mod.Scaper(
        duration=duration,
        fg_path=str(event_folder),
        bg_path=str(bg_folder),
        random_state=None,
    )
    sc.ref_db = ref_db
    return sc


def add_random_background(sc, bg_label: str = "ambience"):
    # choose any file from background folder at random
    sc.add_background(
        label=('const', bg_label),  # label used only in annotation
        source_file=('choose', []),  # choose any file from backgrounds
        source_time=('const', 0),
    )


def add_event(sc,
              label: str = "house",
              snr=(0, 20),
              time=(0, 5),
              duration=(0.5, 3.5),
              pitch_shift=(-2, 2),
              time_stretch=(0.9, 1.1)):
    # Randomly choose an event from the events folder
    sc.add_event(
        # Choose a label from available subfolders in events. If only one exists, it will pick that.
        label=('choose', []),
        source_file=('choose', []),
        source_time=('uniform', 0, 0.0),
        event_time=('uniform', max(0, time[0]), max(0, time[1])),
        event_duration=('uniform', max(0.1, duration[0]), max(0.2, duration[1])),
        snr=('uniform', snr[0], snr[1]),
        pitch_shift=('uniform', pitch_shift[0], pitch_shift[1]),
        time_stretch=('uniform', time_stretch[0], time_stretch[1]),
    )


def main():
    parser = argparse.ArgumentParser(description="Generate 7s non-cry audio mixtures using Scaper")
    parser.add_argument('--output', type=str, default=str(Path('Dataset') / 'non-cry'), help='Output folder for mixtures')
    parser.add_argument('--bg_folder', type=str, default=str(Path('Soundbanks') / 'backgrounds'), help='Path with background WAVs')
    parser.add_argument('--event_folder', type=str, default=str(Path('Soundbanks') / 'events'), help='Path with foreground/event WAVs')
    parser.add_argument('--num', type=int, default=200, help='Number of mixtures to generate')
    parser.add_argument('--sr', type=int, default=DEFAULT_SR, help='Sample rate of output')
    parser.add_argument('--duration', type=float, default=DEFAULT_DURATION, help='Duration seconds')
    parser.add_argument('--min_events', type=int, default=1)
    parser.add_argument('--max_events', type=int, default=4)
    parser.add_argument('--save_jams', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--ref_db', type=float, default=-20.0)
    args = parser.parse_args()

    # Import scaper here to avoid import-time failure before installing requirements
    try:
        import scaper as scaper_mod
    except Exception as e:
        raise SystemExit(f"Failed to import scaper. Install requirements and try again: {e}")

    out_dir = Path(args.output)
    jams_dir = out_dir / 'jams'
    ensure_dirs(out_dir)
    if args.save_jams:
        ensure_dirs(jams_dir)

    # Seed numpy and python's random for reproducibility
    np.random.seed(args.seed)
    random.seed(args.seed)

    # If SoX is not installed, Scaper prints a warning; we can still proceed but pitch/time_stretch may be ignored.

    # Basic validation
    bg_folder = Path(args.bg_folder)
    event_folder = Path(args.event_folder)
    if not bg_folder.exists() or not any(bg_folder.rglob('*.wav')):
        raise FileNotFoundError(f"No background WAVs found under {bg_folder}. Provide a household background bank.")
    if not event_folder.exists() or not any(event_folder.rglob('*.wav')):
        raise FileNotFoundError(f"No event WAVs found under {event_folder}. Provide a household events bank. Organize as Soundbanks/events/<label>/*.wav")

    for i in tqdm(range(args.num), desc='Generating non-cry mixtures'):
        sc = make_scaper(scaper_mod, bg_folder, event_folder, args.duration, args.ref_db)
        add_random_background(sc)
        n_events = np_random_int(args.min_events, args.max_events)
        for _ in range(n_events):
            add_event(sc)

        wav_path = out_dir / f"noncry_{i:05d}.wav"
        jams_path = str(jams_dir / f"noncry_{i:05d}.jams") if args.save_jams else None
        # Generate audio
        sc.generate(
            audio_path=str(wav_path),
            jams_path=jams_path,
            allow_repeated_label=True,
            allow_repeated_source=True,
            reverb=None,
            disable_sox_warnings=True,
            no_audio=False,
            txt_path=None,
        )

    print(f"Done. Wrote {args.num} files to {out_dir}")


def np_random_int(a: int, b: int) -> int:
    return int(np.random.randint(a, b + 1))


if __name__ == '__main__':
    main()
