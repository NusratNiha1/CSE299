import argparse
from pathlib import Path
import os
import shutil
import subprocess
from tqdm import tqdm
try:
    import imageio_ffmpeg
except Exception:
    imageio_ffmpeg = None

TARGET_SR = 16000
TARGET_DUR = 7.0


def find_ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    if imageio_ffmpeg:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def convert(src: Path, dst: Path, ffmpeg_bin: str):
    dst.parent.mkdir(parents=True, exist_ok=True)
    filter_expr = f"apad,atrim=0:{TARGET_DUR}"
    cmd = [ffmpeg_bin, '-y', '-i', str(src), '-ac', '1', '-ar', str(TARGET_SR), '-filter_complex', filter_expr, '-c:a', 'pcm_s16le', str(dst)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout[-400:])


def discover(root: Path):
    exts = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac'}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if Path(fn).suffix.lower() in exts:
                yield Path(dp) / fn


def main():
    ap = argparse.ArgumentParser(description='Standardize non-cry dataset to 7s 16kHz mono WAVs')
    ap.add_argument('--input', type=str, default=str(Path('Dataset') / 'non-cry'))
    ap.add_argument('--output', type=str, default=str(Path('Dataset') / 'non-cry_standardized'))
    ap.add_argument('--prefix', type=str, default='noncry')
    ap.add_argument('--overwrite', action='store_true')
    args = ap.parse_args()

    ffmpeg_bin = find_ffmpeg()
    if not ffmpeg_bin:
        print('[ERROR] ffmpeg not found (system or imageio-ffmpeg). Install or add to requirements.')
        return
    print(f'[INFO] Using ffmpeg at {ffmpeg_bin}')

    in_root = Path(args.input)
    out_root = Path(args.output)
    files = list(discover(in_root))
    if not files:
        print(f'No audio files found under {in_root}')
        return

    for idx, f in enumerate(tqdm(files, desc='Standardizing non-cry')):
        dst = out_root / f'{args.prefix}_{idx:05d}.wav'
        if dst.exists() and not args.overwrite:
            continue
        try:
            convert(f, dst, ffmpeg_bin)
        except Exception as e:
            print(f'[WARN] Failed {f}: {e}')
    print(f'Done. Output: {out_root}')

if __name__ == '__main__':
    main()
