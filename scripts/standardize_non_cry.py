import argparse
from pathlib import Path
import os
import subprocess
import shutil
from tqdm import tqdm
try:
    import imageio_ffmpeg
except Exception:
    imageio_ffmpeg = None

TARGET_SR = 16000
TARGET_DUR = 7.0


def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    if imageio_ffmpeg:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def convert(src: Path, dst: Path, ffmpeg_bin: str):
    filter_expr = f"apad,atrim=0:{TARGET_DUR}"
    cmd = [ffmpeg_bin, '-y', '-i', str(src), '-ac', '1', '-ar', str(TARGET_SR), '-filter_complex', filter_expr, '-c:a', 'pcm_s16le', str(dst)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-400:])


def discover_audio(root: Path):
    exts = {'.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac'}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if Path(fn).suffix.lower() in exts:
                yield Path(dp) / fn


def main():
    ap = argparse.ArgumentParser(description='Standardize non-cry audio to 7s 16k mono wav')
    ap.add_argument('--input', type=str, default='Dataset/non-cry', help='Input non-cry directory (recursive)')
    ap.add_argument('--output', type=str, default='Dataset/non_cry_standardized', help='Output standardized folder')
    ap.add_argument('--prefix', type=str, default='noncry')
    ap.add_argument('--overwrite', action='store_true')
    args = ap.parse_args()

    in_root = Path(args.input)
    out_root = Path(args.output)
    out_root.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        print('[ERROR] ffmpeg not found (system or imageio-ffmpeg). Install it or add to requirements.')
        return
    else:
        print(f'[INFO] Using ffmpeg: {ffmpeg_bin}')

    files = list(discover_audio(in_root))
    if not files:
        print('No audio found to standardize.')
        return

    for i, src in enumerate(tqdm(files, desc='Standardizing non-cry')):
        dst = out_root / f"{args.prefix}_{i:05d}.wav"
        if dst.exists() and not args.overwrite:
            continue
        try:
            convert(src, dst, ffmpeg_bin)
        except Exception as e:
            print(f'[WARN] Failed {src}: {e}')

    print(f'Done. Standardized files in {out_root}')

if __name__ == '__main__':
    main()
