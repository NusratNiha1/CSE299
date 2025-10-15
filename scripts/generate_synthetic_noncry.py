import argparse
from pathlib import Path
import numpy as np
import soundfile as sf
from tqdm import tqdm

"""
Generate synthetic non-cry household audio without Scaper dependency.
Creates varied household-like sounds by layering synthetic backgrounds and events.
"""

SR = 16000
TARGET_DUR = 7.0

def gen_background(duration_s: float):
    """Generate household background ambience"""
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    
    # Low frequency hum (AC, appliances)
    hum_freq = 60 + 80 * np.random.rand()
    hum = 0.2 * np.sin(2 * np.pi * hum_freq * t)
    
    # Slow amplitude modulation
    mod_freq = 0.1 + 0.3 * np.random.rand()
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * mod_freq * t)
    
    # Broadband noise
    noise = 0.03 * np.random.randn(len(t))
    
    return (hum * mod + noise).astype(np.float32)

def gen_beep(duration_s: float):
    """Generate beep/alert sound"""
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    freq = 600 + 1000 * np.random.rand()
    env = np.minimum(1.0, t / 0.01) * np.exp(-4 * t / duration_s)
    return (np.sin(2 * np.pi * freq * t) * env * 0.5).astype(np.float32)

def gen_click():
    """Generate click/tap sound"""
    length = int(0.03 * SR)
    x = np.zeros(length, dtype=np.float32)
    x[0] = 1.0
    decay = np.exp(-np.linspace(0, 8, length))
    noise = 0.2 * np.random.randn(length).astype(np.float32)
    return (x + noise) * decay * 0.3

def gen_whoosh(duration_s: float):
    """Generate air/movement sound"""
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    noise = np.random.randn(len(t)).astype(np.float32)
    # High-pass filter approximation
    hp = np.concatenate([[0], np.diff(noise)])
    env = np.sin(np.pi * t / duration_s)  # fade in/out
    return hp * env * 0.4

def gen_knock(duration_s: float):
    """Generate knock/thud sound"""
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False)
    freq = 80 + 120 * np.random.rand()
    env = np.exp(-10 * t / duration_s)
    return (np.sin(2 * np.pi * freq * t) * env * 0.6).astype(np.float32)

def add_event_at_time(signal, event, start_time_s, snr_db=10):
    """Add an event to signal at specific time with given SNR"""
    start_idx = int(start_time_s * SR)
    end_idx = min(start_idx + len(event), len(signal))
    event_len = end_idx - start_idx
    
    if event_len <= 0:
        return signal
    
    # Calculate SNR scaling
    signal_power = np.mean(signal[start_idx:end_idx] ** 2)
    event_power = np.mean(event[:event_len] ** 2)
    
    if event_power > 1e-10 and signal_power > 1e-10:
        scale = np.sqrt(signal_power / event_power) * (10 ** (snr_db / 20))
    else:
        scale = 1.0
    
    signal[start_idx:end_idx] += event[:event_len] * scale
    return signal

def normalize(x, max_amp=0.9):
    """Normalize audio to max amplitude"""
    peak = np.max(np.abs(x))
    if peak > 1e-10:
        return x / peak * max_amp
    return x

def generate_mixture(duration=TARGET_DUR, n_events=None):
    """Generate one synthetic non-cry mixture"""
    samples = int(SR * duration)
    
    # Start with background
    mix = gen_background(duration)
    
    # Add random number of events
    if n_events is None:
        n_events = np.random.randint(1, 5)
    
    event_funcs = [gen_beep, gen_click, gen_whoosh, gen_knock]
    
    for _ in range(n_events):
        # Choose random event type
        event_func = np.random.choice(event_funcs)
        
        # Generate event with random duration
        if event_func == gen_click:
            event = event_func()
        else:
            event_dur = 0.3 + 2.0 * np.random.rand()
            event = event_func(event_dur)
        
        # Place at random time
        max_start = duration - (len(event) / SR)
        if max_start > 0:
            start_time = max_start * np.random.rand()
            snr = 5 + 15 * np.random.rand()  # 5-20 dB
            mix = add_event_at_time(mix, event, start_time, snr)
    
    return normalize(mix)

def main():
    parser = argparse.ArgumentParser(description='Generate synthetic non-cry household audio')
    parser.add_argument('--output', type=str, default='Dataset/non-cry_standardized', 
                        help='Output folder for generated WAVs')
    parser.add_argument('--num', type=int, default=100, 
                        help='Number of samples to generate')
    parser.add_argument('--duration', type=float, default=TARGET_DUR, 
                        help='Duration in seconds')
    parser.add_argument('--start-index', type=int, default=0,
                        help='Starting file index (for appending)')
    parser.add_argument('--min-events', type=int, default=1)
    parser.add_argument('--max-events', type=int, default=4)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    
    np.random.seed(args.seed)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎵 Generating {args.num} synthetic non-cry samples...")
    print(f"   Duration: {args.duration}s")
    print(f"   Events per sample: {args.min_events}-{args.max_events}")
    print(f"   Output: {out_dir}")
    
    for i in tqdm(range(args.num), desc='Generating'):
        n_events = np.random.randint(args.min_events, args.max_events + 1)
        audio = generate_mixture(args.duration, n_events)
        
        out_path = out_dir / f"noncry_{args.start_index + i:05d}.wav"
        sf.write(str(out_path), audio, SR, subtype='PCM_16')
    
    print(f"✅ Generated {args.num} files to {out_dir}")

if __name__ == '__main__':
    main()
