import argparse
import os
from pathlib import Path
from tqdm import tqdm
import shutil
import subprocess
try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover
    imageio_ffmpeg = None

# Contract
# - Input: root folder with nested subfolders of cry 3gp/wav/etc.
# - Output: flattened 7s mono WAV files at target_sr into Dataset/cry (overwriting optional) or Dataset/cry_merged.
# - Behavior: convert any format readable by pydub/ffmpeg to WAV, resample, trim/pad to exactly duration.
# - Edge cases: shorter files padded with zeros, longer files trimmed; corrupted files skipped with warning.

TARGET_SR = 16000
TARGET_DUR = 7.0  # seconds
TARGET_MS = int(TARGET_DUR * 1000)


def find_ffmpeg() -> str | None:
    # 1. If user has system ffmpeg
    path = shutil.which("ffmpeg")
    if path:
        return path
    # 2. Try imageio-ffmpeg bundled binary
    if imageio_ffmpeg:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def ffmpeg_convert_pad_7s(src: Path, dst: Path, sr: int = TARGET_SR, ffmpeg_bin: str | None = None):
    """Use ffmpeg to convert any input to 7s mono WAV at given sample rate, padding with silence if needed."""
    # filter: apad will add silence to end, atrim enforces exact duration
    filter_expr = f"apad,atrim=0:{TARGET_DUR}"
    exe = ffmpeg_bin or "ffmpeg"
    cmd = [
        exe, "-y",
        "-i", str(src),
        "-ac", "1",
        "-ar", str(sr),
        "-filter_complex", filter_expr,
        "-c:a", "pcm_s16le",
        str(dst),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stdout[-500:]}\nCommand: {' '.join(cmd)}")


def process_file(src_path: Path, dst_path: Path, ffmpeg_bin: str, overwrite: bool = False):
    if dst_path.exists() and not overwrite:
        return
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_convert_pad_7s(src_path, dst_path, TARGET_SR, ffmpeg_bin)
    except Exception as e:
        print(f"[WARN] Failed to process {src_path}: {e}")


def discover_audio_files(root: Path):
    exts = {".3gp", ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if Path(fn).suffix.lower() in exts:
                yield Path(dirpath) / fn


def main():
    parser = argparse.ArgumentParser(description="Flatten and standardize cry audio dataset to 7s WAVs")
    parser.add_argument("--input", type=str, default=str(Path("Dataset") / "cry"), help="Input root folder with nested classes")
    parser.add_argument("--output", type=str, default=str(Path("Dataset") / "cry_merged"), help="Output folder for flattened WAVs")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--prefix", type=str, default="cry", help="Output filename prefix")
    args = parser.parse_args()

    in_root = Path(args.input)
    out_root = Path(args.output)
    out_root.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        print("[ERROR] Could not locate ffmpeg binary. Install system ffmpeg or ensure imageio-ffmpeg installed.")
        return
    else:
        print(f"[INFO] Using ffmpeg binary: {ffmpeg_bin}")

    files = list(discover_audio_files(in_root))
    if not files:
        print(f"No audio files found under {in_root}")
        return

    for idx, f in enumerate(tqdm(files, desc="Processing cry clips")):
        dst = out_root / f"{args.prefix}_{idx:05d}.wav"
        process_file(f, dst, ffmpeg_bin, overwrite=args.overwrite)

    print(f"Done. Wrote WAVs to {out_root}")


if __name__ == "__main__":
    main()
