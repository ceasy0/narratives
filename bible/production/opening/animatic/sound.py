"""The Opening's rough soundtrack, generated in code from the treatment's own rules.

Rule 2 (sound and picture are one thing) is followed literally where it can be: the pair sea's blips
are the same events the picture draws (beats_abstract.make_pair_events), the flips of beat 4 tick
on the frames they flip, the ignitions of beat 8 are the same star times, and the hiss, the whisper,
the laugh and the release are all made from one noise, as the treatment asks (the whisper is the
hiss shaped by a mouth; the laugh is the hiss in pulses; the release's tail is the hiss pitched and
smeared).

Output: stems as 48 kHz stereo float32 arrays, a mixdown WAV, and a cue sheet. Everything here is a
placeholder for the FL Studio arrangement (DOSSIER §6, "Sound, with FL Studio"): the author brings
the stems in, keeps what works and replaces the rest.
"""
from __future__ import annotations

import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DURATION, sstep, rng  # noqa: E402
import beats_abstract as A  # noqa: E402

SR = 48000
B = A.B
N = int(DURATION * SR)
T = np.arange(N, dtype=np.float32) / SR


def env_curve(points):
    """Piecewise-linear envelope over the whole duration from [(t, value), ...]."""
    ts = np.array([p[0] for p in points], np.float32)
    vs = np.array([p[1] for p in points], np.float32)
    return np.interp(T, ts, vs).astype(np.float32)


def db(x):
    return 10 ** (x / 20)


def noise(n, seed):
    return rng(seed).standard_normal(n).astype(np.float32)


def stft_filter(x, gain_fn, nfft=2048, hop=512):
    """Time-varying spectral shaping: gain_fn(t_sec, freqs) -> gain array per frame."""
    win = np.hanning(nfft).astype(np.float32)
    freqs = np.fft.rfftfreq(nfft, 1 / SR).astype(np.float32)
    out = np.zeros(len(x) + nfft, np.float32)
    xp = np.pad(x, (0, nfft))
    for i in range(0, len(x), hop):
        seg = xp[i:i + nfft] * win
        spec = np.fft.rfft(seg)
        spec *= gain_fn(i / SR, freqs)
        out[i:i + nfft] += np.fft.irfft(spec).astype(np.float32) * win
    return out[:len(x)] * (hop / nfft) * 2.0


def logband(freqs, centre, width_oct):
    lf = np.log2(np.maximum(freqs, 1.0))
    return np.exp(-0.5 * ((lf - np.log2(centre)) / width_oct) ** 2).astype(np.float32)


def place(buf, t0, sig, pan=0.0, gain=1.0):
    """Mix a mono signal into the stereo buffer at t0 with equal-power panning (-1..1)."""
    i0 = int(t0 * SR)
    if i0 >= N or i0 + len(sig) <= 0:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    th = (pan + 1) * np.pi / 4
    buf[i0:i0 + n, 0] += sig[:n] * np.cos(th) * gain
    buf[i0:i0 + n, 1] += sig[:n] * np.sin(th) * gain


def blip(f, dur, amp=0.3, shape=0.5, seed=0):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    env = np.exp(-t / (dur * shape)) * np.minimum(1.0, t * 800)
    return (np.sin(2 * np.pi * f * t) * 0.8 + np.sin(2 * np.pi * 2 * f * t) * 0.2) * env * amp


def tone(f_curve, amp_curve, harmonics=((1, 1.0), (2, 0.35), (3, 0.15), (4, 0.06)), vib=0.004, vib_rate=4.7, seed=0):
    """A sustained tone whose pitch and level are curves over the whole duration.

    v3 fix: v1 and v2 multiplied the running phase by the vibrato, so the pitch swing grew with time
    (by 1:40 the held A3 was swinging by more than a thousand hertz, four and a half times a second).
    That was the "1980s alien" oscillation. Vibrato now modulates the frequency, and the phase is the
    integral of it, so the swing stays as small as it's set."""
    lfo = np.sin(2 * np.pi * vib_rate * T + seed) * 0.6 + np.sin(2 * np.pi * vib_rate * 0.37 * T + 2 * seed) * 0.4
    ph = np.cumsum(f_curve.astype(np.float64) * (1 + vib * lfo)) / SR  # float64: float32 loses the phase by 1:00
    out = np.zeros(N, np.float32)
    for h, a in harmonics:
        out += a * np.sin(2 * np.pi * ((h * ph) % 1.0)).astype(np.float32)
    return out * amp_curve


def lowpass_env(x, cutoff_fn):
    return stft_filter(x, lambda t, f: (1 / (1 + (f / cutoff_fn(t)) ** 4)).astype(np.float32))


# ------------------------------------------------------------------------- the stems

def stem_hiss():
    """Beat 1, v3: the deep as a soundscape, not a hiss alone. Wind over open water (two noise bands
    that gust independently, left and right), sand pouring (a fine crackle of grains that thickens as
    the static starts to flow), and far under it a low swell like the sea heard through rock. It all
    comes up out of silence from the first frame, a little ahead of the picture. From 0:26 it narrows
    and climbs, like a breath drawn in that doesn't stop."""
    out = np.zeros((N, 2), np.float32)
    nb = int((B["light"] + 0.1) * SR)  # the hiss lives in beat 1; nothing of it after the release
    TT = T[:nb]

    def wind(seed):
        x = noise(nb, seed)

        def gain(t, f):
            climb = sstep(26.0, 38.0, t)
            gust = 0.75 + 0.25 * np.sin(t * 0.31 + seed) * np.sin(t * 0.13 + 2 * seed)
            centre = 650 * (1 + 0.25 * np.sin(t * 0.21 + seed)) * (2 ** (climb * 2.7))
            width = 2.0 - 1.5 * climb
            return logband(f, centre, width) * (f > 50) * gust

        return stft_filter(x, gain)

    L, R = wind(1), wind(2)
    level = np.interp(TT, [0, 1.0, 4.0, 8.0, 26, 37.9, 38.0], [0.0, 0.05, 0.35, 1.0, 1.0, db(10), 0.0]).astype(np.float32)
    out[:nb, 0] += L * level * 0.05
    out[:nb, 1] += R * level * 0.05

    # sand: single grains as tiny clicks, more of them as the current starts (0:12) and as it climbs
    r = rng(31)
    t = 0.5
    sand = np.zeros((nb, 2), np.float32)
    while t < B["light"]:
        rate = 30 + 400 * sstep(10.0, 20.0, t) + 600 * sstep(26.0, 38.0, t)
        n = int(r.uniform(0.0006, 0.002) * SR)
        click = noise(n, int(t * 9973) % 100000) * np.exp(-np.arange(n) / (n * 0.3))
        i0 = int(t * SR)
        pan = r.uniform(-1, 1)
        th = (pan + 1) * np.pi / 4
        amp = r.uniform(0.2, 1.0) * float(np.interp(t, [0, 3, 10, 38], [0, 0.3, 1.0, 1.4]))
        if i0 + n < nb:
            sand[i0:i0 + n, 0] += click * np.cos(th) * amp
            sand[i0:i0 + n, 1] += click * np.sin(th) * amp
        t += r.exponential(1.0 / rate)
    hp = lambda ts, f: (f / 2500) ** 2 / (1 + (f / 2500) ** 2) * logband(f, 6000, 1.5)
    out[:nb, 0] += stft_filter(sand[:, 0], hp) * 0.05
    out[:nb, 1] += stft_filter(sand[:, 1], hp) * 0.05

    # the deep: a low swell, below where the ear finds pitch, rising with the climb
    sub = noise(nb, 33)

    def subg(ts, f):
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * ts / 9.0) ** 2
        return logband(f, 45 * (2 ** (0.8 * sstep(26, 38, ts))), 0.7) * swell

    sb = stft_filter(sub, subg)
    lvl = np.interp(TT, [0, 2, 10, 26, 38, 38.05], [0, 0.2, 1.0, 1.0, 2.2, 0.0]).astype(np.float32)
    out[:nb, 0] += sb * lvl * 0.10
    out[:nb, 1] += sb * lvl * 0.10
    return out


def stem_whisper():
    """The same noise shaped like breath passing through an open mouth and throat: formants, no voice.
    It sits where the face is (the centre), and from 0:26 it draws in with the climb."""
    x = noise(N, 3)

    def gain(t, f):
        climb = sstep(26.0, 38.0, t)
        g = np.zeros_like(f)
        for fc, bw, a in ((520, 0.25, 1.0), (1500, 0.2, 0.7), (2500, 0.18, 0.45)):
            g += a * logband(f, fc * (1 + 0.8 * climb), bw)
        breath = 0.55 + 0.45 * np.sin(2 * np.pi * t / 4.5 - 1.2)  # slow breathing
        return g * (0.3 + 0.7 * breath)

    w = stft_filter(x, gain)
    level = env_curve([(0, 0), (15.5, 0), (20, 0.5), (27, 1.0), (37.9, 1.0 * db(6)), (38.0, 0), (DURATION, 0)])
    return np.stack([w, w], axis=1) * level[:, None] * 0.09


def stem_release():
    """The release at 0:38, v3: layered, the way a film hit is built, not one sine.

    1. the in-breath's last second: the climb's noise reversed into the hit, so the hit is sucked in;
    2. the body: a sub-bass drop from 55 to 28 Hz, distorted, two seconds long;
    3. the punch: a mid thump and a transient, so it hits on small speakers too;
    4. the blast: a wide noise burst swept from bright to dark;
    5. the tail: the static itself, pitched and smeared, passing the ears and shutting behind the head;
    6. the air: a long, dark reverb bloom under all of it, the size of a cathedral, dying away to
       silence by about 0:44, out of which the held note rises when the eyes open.
    The atmosphere (stem_atmos) adds a sustained shimmer that blooms from the hit and fades with it."""
    buf = np.zeros((N, 2), np.float32)
    t0 = B["light"]
    # 1. the suck: noise swelling into the hit, reversed decay, bright
    nr = int(1.2 * SR)
    tr = np.arange(nr, dtype=np.float32) / SR
    sw = stft_filter(noise(nr, 40), lambda ts, f: logband(f, 2500 + 5000 * ts / 1.2, 1.2))
    sw *= (tr / 1.2) ** 3
    place(buf, t0 - 1.2, sw, -0.4, 0.35)
    place(buf, t0 - 1.2, sw[::-1][::-1] * 0.9, 0.4, 0.35)
    # 2. the body
    n = int(2.6 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 55 * np.exp(-t / 0.6) + 28
    ph = np.cumsum(f.astype(np.float64)) / SR
    body = np.sin(2 * np.pi * (ph % 1.0)).astype(np.float32) * np.exp(-t / 1.1)
    body = np.tanh(body * 5.0) * 0.9
    body = stft_filter(body, lambda ts, fr: 1 / (1 + (fr / 180) ** 4))
    place(buf, t0, body, 0.0, 1.0)
    # 3. the punch
    npun = int(0.35 * SR)
    tp = np.arange(npun, dtype=np.float32) / SR
    punch = np.sin(2 * np.pi * (140 * np.exp(-tp / 0.05) + 70) * tp) * np.exp(-tp / 0.08)
    punch = np.tanh(punch * 3) * 0.8
    click = noise(int(0.008 * SR), 4) * np.linspace(1, 0, int(0.008 * SR))
    punch[:len(click)] += click * 0.6
    place(buf, t0, punch, 0.0, 0.8)
    # 4. the blast
    nbl = int(1.6 * SR)
    tb = np.arange(nbl, dtype=np.float32) / SR
    for side, seed in ((-0.8, 41), (0.8, 42)):
        bl = stft_filter(noise(nbl, seed), lambda ts, fr: logband(fr, 7000 * 2 ** (-ts * 4.0) + 150, 1.6))
        bl *= np.exp(-tb / 0.35) * np.minimum(1, tb * 400)
        place(buf, t0, bl, side, 0.55)
    # 5. the tail: the static passing the ears, front to back
    nt = int(1.9 * SR)
    tail_src = noise(nt, 5)
    tt = np.arange(nt, dtype=np.float32) / SR

    def gain(tsec, fr):
        k = min(tsec / 1.6, 1.0)
        centre = 5000 * (2 ** (-k * 4.2))
        return logband(fr, centre, 0.9) * (1 - k) ** 1.5

    tail = stft_filter(tail_src, gain) * np.exp(-tt / 0.7)
    d = int(0.004 * SR)
    place(buf, t0, tail, -1.0, 0.7)
    place(buf, t0, -np.concatenate([np.zeros(d, np.float32), tail[:-d]]), 1.0, 0.7)
    # 6. the air: its own long reverb, dark, so the hit blooms and dies away in six seconds
    seg = buf[int((t0 - 1.3) * SR):int((t0 + 3.0) * SR)].copy()
    ir = reverb_ir(6.5, rt_low=5.5, rt_high=1.6, seed=77, predelay=0.03)
    wet = convolve(seg, ir)
    i0 = int((t0 - 1.3) * SR)
    m = min(len(wet), N - i0)
    buf[i0:i0 + m] += wet[:m] * 0.22
    # true silence after: nothing of the release lasts past 0:45.5 (the note rises out of the end of it)
    fade = np.interp(T, [0, t0 + 5.0, t0 + 7.4, DURATION], [1, 1, 0, 0]).astype(np.float32)
    return buf * fade[:, None]


def stem_note():
    """One held note that belongs to whatever we're watching, from the eyes opening to the cliff.

    v3: a steady, warm, sustained tone, not an oscillation (see tone()). Three voices a few cents
    apart give it a slow living shimmer and width instead of a wobble; the pitch glides between beats
    over two or three seconds; a soft breath of air rides on its upper harmonics."""
    # pitch by beat (Hz): faces A2, the grain up a fifth then an octave, the proton a third voice,
    # the photon high and pure, then down with the world: cell E4, animal A3, people E3, the face A2.
    f = env_curve([
        (0, 110), (B["sep"], 110), (B["eve"], 110), (B["eve"] + 10, 165), (B["vault"], 220),
        (B["land"] + 3, 220), (B["earth"], 196), (B["lights"], 196), (B["lights"] + 12, 247), (B["cross"] - 1, 880),
        (B["cross"], 880), (B["swarm"] - 2, 880), (B["swarm"] + 1, 330), (B["landbeat"], 330), (B["landbeat"] + 3, 220),
        (B["dust"], 220), (B["dust"] + 3, 196), (B["fill"], 196), (B["fill"] + 3, 165),
        (B["rest"], 165), (B["rest"] + 3, 110), (DURATION, 110)])
    amp = env_curve([
        (0, 0), (B["light"] + 6.4, 0), (B["light"] + 8.5, 0.12), (B["sep"] + 12, 0.16), (B["sep"] + 13, 0.10), (B["eve"], 0.10),
        (B["vault"], 0.15), (B["cross"], 0.20), (B["cross"] + 6, 0.16), (B["swarm"], 0.14), (B["fill"], 0.10),
        (B["rest"], 0.10), (B["rest"] + 17, 0.10), (B["rest"] + 22, 0.0), (DURATION, 0)])
    purity = env_curve([(0, 0.3), (B["lights"] + 12, 0.3), (B["cross"], 1.0), (B["swarm"], 0.4), (DURATION, 0.3)])
    warm_h = ((1, 0.0), (2, 0.32), (3, 0.16), (4, 0.07), (5, 0.035), (6, 0.015))
    L = np.zeros(N, np.float32)
    R = np.zeros(N, np.float32)
    for k, (cents, pan) in enumerate(((0.0, 0.0), (-4.0, -0.6), (4.0, 0.6))):
        fk = f * 2 ** (cents / 1200)
        base = tone(fk, amp, harmonics=((1, 1.0),), vib=0.0015, vib_rate=0.23 + 0.05 * k, seed=k)
        warm = tone(fk, amp, harmonics=warm_h, vib=0.0015, vib_rate=0.23 + 0.05 * k, seed=k)
        v = (base + warm * (1 - purity)) * (0.6 if k == 0 else 0.45)
        th = (pan + 1) * np.pi / 4
        L += v * np.cos(th)
        R += v * np.sin(th)
    # the proton: two more voices lock in at 106-109 s (a fifth and an octave), and stay through the atom
    kp = env_curve([(0, 0), (B["land"] + 2.5, 0), (B["land"] + 5, 1), (B["earth"] + 6, 1), (B["lights"] + 10, 0), (DURATION, 0)])
    v5 = tone(f * 1.5, amp * 0.5 * kp, harmonics=((1, 1.0), (2, 0.2)), vib=0.001, vib_rate=0.31, seed=5)
    v8 = tone(f * 2.0, amp * 0.35 * kp, harmonics=((1, 1.0),), vib=0.001, vib_rate=0.27, seed=6)
    L += v5 * 0.8 + v8 * 0.6
    R += v5 * 0.6 + v8 * 0.8
    # air: noise breathing on the 4th-6th harmonics, very quiet
    air = noise(N, 61)

    def ag(ts, fr):
        i = min(int(ts * SR), N - 1)
        return logband(fr, float(f[i]) * 5, 0.35) * 0.5

    a_ = stft_filter(air, ag) * amp * 0.15 * (1 - purity * 0.5)
    L += a_
    R += a_
    return np.stack([L, R], axis=1)


def stem_atmos():
    """v3, new: the atmosphere the author asked for ("much more atmospheric, like a soundscape").
    Slow pads and textures around the held note, in its key, that change with each beat's color:

    - the release's bloom: a high shimmer (octaves of A, slowly beating) that rises out of the hit and
      fades into the silence before the eyes open;
    - beat 3, the separation: a low, close cluster under the laugh (A, B flat, E flat: the tension of
      a tritone), swelling with the climb; then at the turn-over an open fifth and octave, warm;
    - beat 4: the two chords trading with the turns, then dissolving into a granular cloud of the note's
      own partials as the grains take over;
    - beats 5-8: the cosmos, a wide pad of fifths with a shimmer of high partials drifting across the
      stereo field, slowly filtered open and shut; it thins as the glare clears and swells in the star;
    - beat 9: nothing (the note alone, as the treatment says);
    - from beat 10: a very low bed under the world sounds, darkening to almost nothing at the cliff."""
    out = np.zeros((N, 2), np.float32)
    A = 55.0

    def pad(freqs, env, bright, seed, detune=6.0, width=0.8):
        L = np.zeros(N, np.float32)
        R = np.zeros(N, np.float32)
        for j, fq in enumerate(freqs):
            for k, c in enumerate((-detune, 0.0, detune)):
                fc = env_curve([(0, fq), (DURATION, fq)]) * 2 ** (c / 1200)
                h = ((1, 1.0), (2, 0.5 * bright), (3, 0.33 * bright), (4, 0.22 * bright), (5, 0.15 * bright), (6, 0.1 * bright))
                v = tone(fc, env, harmonics=h, vib=0.002, vib_rate=0.11 + 0.03 * k + 0.02 * j, seed=seed + 3 * j + k)
                pan = (k - 1) * width * (1 if j % 2 == 0 else -1)
                th = (pan + 1) * np.pi / 4
                L += v * np.cos(th)
                R += v * np.sin(th)
        return np.stack([L, R], 1) / (3 * len(freqs))

    # the release's shimmer: A5, A6 and E7, beating, out of the hit and gone by 0:44
    env = env_curve([(0, 0), (B["light"], 0), (B["light"] + 0.3, 0.5), (B["light"] + 2.5, 0.25), (B["light"] + 6.0, 0.0), (DURATION, 0)])
    out += pad([A * 16, A * 32, A * 48], env, 0.1, 100, detune=9.0) * 0.5
    # beat 3: separation
    sep_env = env_curve([(0, 0), (B["light"] + 7.5, 0), (B["sep"], 0.3), (B["sep"] + 11, 1.0), (B["sep"] + 12.5, 1.0), (B["sep"] + 12.6, 0.0), (DURATION, 0)])
    out += pad([A, A * 2 ** (1 / 12) * 2, A * 2 ** (6 / 12) * 2], sep_env, 0.9, 200, detune=10.0) * 0.6
    con_env = env_curve([(0, 0), (B["sep"] + 12.5, 0), (B["sep"] + 12.8, 1.0), (B["eve"] - 1, 0.6), (B["eve"], 0.3), (B["eve"] + 8, 0.25), (B["eve"] + 14, 0), (DURATION, 0)])
    out += pad([A, A * 1.5 * 2, A * 4], con_env, 0.6, 300) * 0.6
    sep2 = env_curve([(0, 0), (B["eve"], 0), (B["eve"] + 0.2, 0.5), (B["eve"] + 8, 0.35), (B["eve"] + 14, 0), (DURATION, 0)])
    out += pad([A, A * 2 ** (1 / 12) * 2, A * 2 ** (6 / 12) * 2], sep2, 0.9, 210, detune=10.0) * 0.4
    # the cosmos
    cos_env = env_curve([(0, 0), (B["eve"] + 9, 0), (B["vault"] + 2, 0.8), (B["land"] + 10, 0.6), (B["earth"], 0.7),
                         (B["lights"] + 8, 0.9), (B["lights"] + 12, 1.1), (B["cross"] - 0.5, 0.6), (B["cross"], 0.0), (DURATION, 0)])
    cosmos = pad([A * 2, A * 3, A * 4, A * 6], cos_env, 0.5, 400, detune=7.0, width=1.0)

    def sweep(ts, fr):
        cut = 600 * 2 ** (2.5 * (0.5 + 0.5 * np.sin(2 * np.pi * ts / 13.0)))
        return 1 / (1 + (fr / cut) ** 2)

    out[:, 0] += stft_filter(cosmos[:, 0], sweep) * 0.9
    out[:, 1] += stft_filter(cosmos[:, 1], sweep) * 0.9
    # the shimmer of high partials: short soft grains of the note's harmonics, drifting in stereo
    r = rng(500)
    t = B["eve"] + 8.0
    while t < B["cross"] - 0.5:
        dur = r.uniform(0.25, 1.2)
        n = int(dur * SR)
        tt = np.arange(n, dtype=np.float32) / SR
        f0 = A * 2 ** r.integers(3, 6) * [1, 1.5, 2, 2.5, 3][r.integers(0, 5)]
        g_ = np.sin(2 * np.pi * f0 * tt) * np.sin(np.pi * tt / dur) ** 2
        k = float(np.interp(t, [B["eve"] + 8, B["vault"] + 2, B["land"] + 12, B["lights"], B["cross"] - 0.5], [0, 1.0, 0.5, 0.8, 0.0]))
        place(out, t, g_, r.uniform(-1, 1), 0.012 * k)
        t += r.exponential(0.06)
    # the world's bed
    w_env = env_curve([(0, 0), (B["swarm"], 0), (B["swarm"] + 3, 0.5), (B["fill"], 0.4), (B["rest"], 0.25), (B["rest"] + 20, 0.0), (DURATION, 0)])
    out += pad([A, A * 1.5, A * 2], w_env, 0.3, 600) * 0.5
    return out


# ------------------------------------------------------------------------- space

def reverb_ir(seconds, rt_low=4.0, rt_high=1.2, seed=0, predelay=0.02):
    """A stereo impulse response made of noise that decays faster in the highs than in the lows, as a
    big stone room or open air at night does. rt_*: seconds to fall 60 dB."""
    n = int(seconds * SR)
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros((n, 2), np.float32)
    bands = ((60, 400, rt_low), (400, 2000, (rt_low + rt_high) / 2), (2000, 20000, rt_high))
    for ch in range(2):
        x = noise(n, seed + ch)
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(n, 1 / SR)
        y = np.zeros(n, np.float32)
        for lo, hi, rt in bands:
            Xb = np.where((fr >= lo) & (fr < hi), X, 0)
            yb = np.fft.irfft(Xb, n).astype(np.float32)
            y += yb * np.exp(-6.91 * t / rt)
        # a soft attack, so the room blooms rather than clicks
        y *= np.minimum(1.0, t / 0.08)
        out[:, ch] = y
    d = int(predelay * SR)
    out = np.concatenate([np.zeros((d, 2), np.float32), out])[:n]
    return out / np.sqrt((out ** 2).sum(0, keepdims=True) + 1e-9)


def convolve(x, ir):
    """Overlap-add FFT convolution, stereo in, stereo out (left with left, right with right)."""
    n, m = len(x), len(ir)
    blk = 1 << 18
    nfft = 1 << int(np.ceil(np.log2(blk + m - 1)))
    out = np.zeros((n + m - 1, 2), np.float32)
    for ch in range(2):
        H = np.fft.rfft(ir[:, ch], nfft)
        for i in range(0, n, blk):
            seg = x[i:i + blk, ch]
            y = np.fft.irfft(np.fft.rfft(seg, nfft) * H, nfft)[:len(seg) + m - 1]
            out[i:i + len(y), ch] += y.astype(np.float32)
    return out


def stem_laugh():
    """The laugh carried by the hiss: hard pulses in the rhythm of laughter, no voice. 52-58 s. Then,
    in beat 4, each dark turn brings it back, shorter each time."""
    buf = np.zeros((N, 2), np.float32)
    r = rng(6)

    def pulses(t0, t1, grow):
        t = t0
        while t < t1:
            gap = r.uniform(0.16, 0.26)
            dur = gap * 0.7
            n = int(dur * SR)
            tt = np.arange(n, dtype=np.float32) / SR
            src = noise(n, int(t * 1000) % 100000)
            x = stft_filter(src, lambda ts, f: logband(f, 1800, 0.8))
            env = np.sin(np.pi * tt / dur) ** 0.6
            k = (t - t0) / (t1 - t0)
            place(buf, t, x * env * (0.25 + 0.75 * k) ** grow, r.uniform(-0.6, 0.6), 0.5)
            t += gap

    pulses(B["sep"] + 6.0, B["sep"] + 12.3, 1.0)
    # beat 4: the dark phases
    _, n_cont = A.flip_count(np.array([0.0]))
    starts = [0.0]
    a, ratio = A._FLIP_A, A._FLIP_R
    tt = 0.0
    for i in range(14):
        tt += a * ratio ** i
        starts.append(tt)
    for i in range(0, len(starts) - 1, 2):
        t0 = B["eve"] + starts[i]
        t1 = B["eve"] + starts[i + 1]
        if t1 - t0 > 0.3:
            pulses(t0, t1, 0.5)
    return buf


def stem_grains():
    """Beat 4: a tick for each turn-over while the whole frame turns; then the ticks spread into a
    granular shimmer, and the first color brings the first pitched grains. Beats 5-6: the pair sea's
    own events as blips, pitch from hue, pan from x, loud by nearness."""
    buf = np.zeros((N, 2), np.float32)
    r = rng(7)
    # ticks on the flips
    a, ratio = A._FLIP_A, A._FLIP_R
    tt = 0.0
    for i in range(16):
        n = int(0.03 * SR)
        tick = noise(n, 50 + i) * np.exp(-np.arange(n) / (n * 0.25))
        place(buf, B["eve"] + tt, tick, 0.0, 0.5 * (0.9 ** i))
        tt += a * ratio ** i
    # the spread: many small grains, more and more, each on its own beat
    t = B["eve"] + 3.2
    while t < B["vault"] + 1.0:
        k = sstep(B["eve"] + 3.2, B["eve"] + 12, t)
        rate = 8 + 300 * k
        n = int(r.uniform(0.004, 0.02) * SR)
        g = noise(n, int(t * 10000) % 100000) * np.sin(np.pi * np.arange(n) / n)
        place(buf, t, g, r.uniform(-1, 1), 0.12 * (1 - 0.5 * k))
        # the first color: pitched grains, from a pentatonic
        if t > B["eve"] + 9.0 and r.random() < 0.35:
            scale = [0, 2, 4, 7, 9]
            f = 220 * 2 ** (r.integers(0, 3) + scale[r.integers(0, 5)] / 12)
            place(buf, t, blip(f, 0.08, 0.2, 0.5), r.uniform(-1, 1), 0.5 * sstep(B["eve"] + 9, B["eve"] + 15, t))
        t += 1.0 / rate * r.uniform(0.5, 1.5)
    # the pair sea: the same events the picture draws
    P = A.make_pair_events(20261008)
    cam_speed = 0.35
    for i in range(len(P["birth"])):
        tb = float(P["birth"][i])
        if tb < B["vault"] or tb > B["land"] + 9:
            continue
        cam_z = (tb - B["vault"]) * cam_speed
        d = float(P["z"][i] + cam_z - cam_z)  # the sea moves with the camera; z is the distance
        if d > 1.6:
            continue
        if r.random() > 0.5:
            continue
        scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
        f = 330 * 2 ** (scale[int(P["hue"][i] * len(scale)) % len(scale)] / 12)
        thin = 1 - sstep(B["land"] + 3, B["land"] + 9, tb)
        amp = 0.25 / (d ** 1.2) * thin
        pan = float(np.clip(P["x"][i] / (d * 2.0), -1, 1))
        place(buf, tb, blip(f, float(P["life"][i]) * 0.5, amp, 0.5), pan, 0.5)
    return buf


def stem_cosmos():
    """Beats 6-9: the electron's ping; the gas as a pad; the ignitions; the fall into the star; the
    interior's roar and two impacts; the photon's flight (nothing); the Earth's first wind; the cloud;
    the water."""
    buf = np.zeros((N, 2), np.float32)
    r = rng(8)
    # the electron: a high ping each orbit from 111 s, fading as the glare clears
    t = B["land"] + 7.0
    while t < B["earth"] + 6:
        place(buf, t, blip(1760, 0.15, 0.12, 0.4), 0.3 * np.sin(t * 9), 0.6 * (1 - sstep(B["earth"], B["earth"] + 6, t)))
        t += 2 * np.pi / 11.0
    # the gas: a soft pad of low harmonics, swelling as it draws into threads
    pad_amp = env_curve([(0, 0), (B["land"] + 10, 0), (B["earth"], 0.06), (B["earth"] + 8, 0.12), (B["lights"] + 8, 0.08), (B["lights"] + 12, 0), (DURATION, 0)])
    pad = tone(env_curve([(0, 98), (DURATION, 98)]), pad_amp, harmonics=((1, 1.0), (1.5, 0.5), (2, 0.4), (3, 0.2), (4, 0.1)), vib=0.002)
    buf[:, 0] += pad
    buf[:, 1] += pad
    # ignitions: bright attacks at the stars' own times; bursts as low booms
    W = A.make_web_points(91)
    stars = A.web_stars()  # the same stars, in the same places, as the picture (beat_lights)
    for i in range(min(len(stars), len(W["ignite"]))):
        t0 = B["lights"] + float(W["ignite"][i])
        n = int(0.6 * SR)
        tt = np.arange(n, dtype=np.float32) / SR
        src = noise(n, 200 + i)
        x = stft_filter(src, lambda ts, f: logband(f, 6000 * np.exp(-ts * 2.5) + 800, 0.7))
        x = x * np.exp(-tt / 0.18)
        pan = float(np.clip(stars[i][0] / 1.78, -1, 1))
        place(buf, t0, x, pan, 0.35)
        place(buf, t0, blip(1320 * (1 + 0.3 * r.random()), 0.5, 0.12, 0.6), pan, 0.5)
        if W["burst"][i]:
            tb = t0 + float(W["burst_t"][i])
            nb = int(1.2 * SR)
            tb_ = np.arange(nb, dtype=np.float32) / SR
            boom = np.sin(2 * np.pi * (45 * np.exp(-tb_ / 0.4) + 30) * tb_) * np.exp(-tb_ / 0.5)
            place(buf, tb, np.tanh(boom * 2.5) * 0.5, pan, 0.6)
    # falling in: a rising roar, then the interior's hot noise; two impacts; the photon's leaving
    n = int((B["cross"] - (B["lights"] + 8)) * SR)
    tt = np.arange(n, dtype=np.float32) / SR
    src = noise(n, 300)

    def gain(ts, f):
        k = sstep(0, 4.0, ts)
        out_ = sstep(12.5, 14.0, ts)
        centre = 150 * (2 ** (k * 3.5))
        return logband(f, centre, 1.4) * (0.2 + 0.8 * k) * (1 - out_)

    roar = stft_filter(src, gain)
    place(buf, B["lights"] + 8, roar, 0.0, 0.5)
    for ti, amp in ((B["lights"] + 12 + 2.5, 0.6), (B["lights"] + 12 + 4.5, 0.8)):
        nb = int(1.0 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        hit = np.sin(2 * np.pi * (70 * np.exp(-tb_ / 0.25) + 35) * tb_) * np.exp(-tb_ / 0.4)
        place(buf, ti, np.tanh(hit * 3) * amp, 0.0, 0.8)
    # the Earth's first wind, the cloud, the water
    n = int(14 * SR)
    tt = np.arange(n, dtype=np.float32) / SR
    src = noise(n, 400)

    def gain2(ts, f):
        t_abs = B["cross"] + ts
        wind = sstep(B["cross"] + 7, B["cross"] + 10, t_abs) * (1 - sstep(B["cross"] + 11.3, B["cross"] + 11.6, t_abs))
        cloud = sstep(B["cross"] + 10, B["cross"] + 11.2, t_abs) * (1 - sstep(B["cross"] + 11.4, B["cross"] + 11.6, t_abs))
        under = sstep(B["cross"] + 11.5, B["cross"] + 11.8, t_abs)
        g = logband(f, 400, 1.5) * wind * 0.6 + logband(f, 2500, 1.2) * cloud * 1.2 + logband(f, 120, 1.0) * under * 0.8
        return g

    w = stft_filter(src, gain2)
    place(buf, B["cross"], w, 0.0, 0.5)
    # the surface broken: a muffled whoosh
    nb = int(0.8 * SR)
    tb_ = np.arange(nb, dtype=np.float32) / SR
    splash = stft_filter(noise(nb, 401), lambda ts, f: logband(f, 300 + 2000 * np.exp(-ts * 6), 1.0)) * np.exp(-tb_ / 0.3)
    place(buf, B["cross"] + 11.5, splash, 0.0, 0.7)
    return buf


def stem_world():
    """From beat 10 real sounds take over: water, divisions, the great creature, wings, surf, insects,
    crickets, the quake, the sky falling, wind, feet, voices without words, the river, birds, breath."""
    buf = np.zeros((N, 2), np.float32)
    r = rng(9)
    n = int((DURATION - B["swarm"]) * SR)
    src_a = noise(n, 500)
    src_b = noise(n, 501)

    def bed(ts, f):
        t = B["swarm"] + ts
        g = np.zeros_like(f)
        # underwater: beats 10
        under = sstep(B["swarm"], B["swarm"] + 1, t) * (1 - sstep(B["landbeat"], B["landbeat"] + 2, t))
        g += logband(f, 150, 1.0) * under * 0.7 * (0.8 + 0.2 * np.sin(t * 0.9))
        # surf and air: beat 11 day
        shore = sstep(B["landbeat"], B["landbeat"] + 2, t) * (1 - sstep(B["landbeat"] + 11, B["landbeat"] + 13, t))
        g += logband(f, 900, 1.6) * shore * 0.35 * (0.5 + 0.5 * np.sin(t * 0.5) ** 2)
        # night: a low hush; crickets are separate
        night = sstep(B["landbeat"] + 11, B["landbeat"] + 13, t) * (1 - sstep(B["landbeat"] + 19.5, B["landbeat"] + 21, t))
        g += logband(f, 200, 1.2) * night * 0.15
        # the glow, the quake, the sky falling: a rumble that climbs to a roar
        glow = sstep(B["landbeat"] + 23, B["landbeat"] + 27, t)
        quake = sstep(B["landbeat"] + 25.8, B["landbeat"] + 26.3, t) * (1 - sstep(B["landbeat"] + 27.5, B["landbeat"] + 28.5, t))
        fall = sstep(B["landbeat"] + 27.5, B["dust"] + 1.0, t) * (1 - sstep(B["dust"] + 1.0, B["dust"] + 4.0, t))
        g += logband(f, 45, 0.8) * (glow * 0.7 + quake * 1.5)
        g += logband(f, 300 + 1500 * fall, 1.6) * fall * 1.3
        # the long dark: wind, then hush; wind through the green
        wind = sstep(B["dust"] + 2, B["dust"] + 6, t) * (1 - sstep(B["dust"] + 15, B["dust"] + 17, t))
        g += logband(f, 500, 1.4) * wind * 0.3 * (0.6 + 0.4 * np.sin(t * 0.4 + 1) ** 2)
        still = sstep(B["dust"] + 16, B["dust"] + 17.5, t) * (1 - sstep(B["fill"], B["fill"] + 0.5, t))
        g += logband(f, 400, 1.6) * still * 0.08
        # the band: forest air, then open ground, then the river
        band = sstep(B["fill"], B["fill"] + 1, t) * (1 - sstep(B["rest"] + 1, B["rest"] + 3, t))
        g += logband(f, 600, 1.6) * band * 0.12
        river = sstep(B["fill"] + 29, B["fill"] + 33, t) * (1 - sstep(B["rest"] + 8, B["rest"] + 12, t))
        g += logband(f, 1200, 1.4) * river * 0.3
        # the cliff: wind, and nothing else
        cliff = sstep(B["rest"], B["rest"] + 3, t) * (1 - sstep(B["rest"] + 22.5, B["rest"] + 23.2, t))
        g += logband(f, 350, 1.5) * cliff * 0.35 * (0.6 + 0.4 * np.sin(t * 0.3) ** 2)
        return g

    L = stft_filter(src_a, bed)
    R = stft_filter(src_b, bed)
    buf[int(B["swarm"] * SR):int(B["swarm"] * SR) + n, 0] += L * 0.6
    buf[int(B["swarm"] * SR):int(B["swarm"] * SR) + n, 1] += R * 0.6

    # divisions: soft pops
    for x in (2.0, 4.4, 6.2, 7.6, 8.7, 9.6, 10.3):
        place(buf, B["swarm"] + x + 0.45, blip(180, 0.12, 0.25, 0.3), 0.0, 0.5)
    # the great creature: a deep pass
    nb = int(4 * SR)
    tb_ = np.arange(nb, dtype=np.float32) / SR
    deep = np.sin(2 * np.pi * (40 - 8 * tb_ / 4) * tb_) * np.sin(np.pi * tb_ / 4) ** 0.5
    place(buf, B["swarm"] + 26.5, deep * 0.4, 0.0, 0.7)
    # wings over the water, then insects, then crickets
    t = B["swarm"] + 30
    while t < B["landbeat"] + 8:
        nb = int(0.25 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        fl = noise(nb, int(t * 100) % 10000) * (np.sin(2 * np.pi * 14 * tb_) ** 2) * np.sin(np.pi * tb_ / 0.25)
        fl = stft_filter(fl, lambda ts, f: logband(f, 1500, 1.0))
        place(buf, t, fl, r.uniform(-1, 1), 0.25)
        t += r.uniform(0.3, 1.2)
    t = B["landbeat"]
    while t < B["landbeat"] + 12:
        f0 = r.uniform(3000, 5000)
        nb = int(r.uniform(0.3, 1.5) * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        buzz = np.sin(2 * np.pi * f0 * tb_) * (0.6 + 0.4 * np.sin(2 * np.pi * 180 * tb_)) * np.sin(np.pi * tb_ / (nb / SR))
        place(buf, t, buzz, r.uniform(-1, 1), 0.03)
        t += r.uniform(0.2, 0.8)
    t = B["landbeat"] + 12
    while t < B["landbeat"] + 25.5:
        nb = int(0.06 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        ch = np.sin(2 * np.pi * 4200 * tb_) * np.sin(np.pi * tb_ / 0.06)
        for k in range(3):
            place(buf, t + k * 0.09, ch, 0.6, 0.05 * (1 - sstep(B["landbeat"] + 23.5, B["landbeat"] + 25.5, t)))
        t += 0.5 + 0.1 * r.random()
    # the sky falling: streaks, each a short descending whistle, more and more of them
    t = B["landbeat"] + 27.6
    while t < B["dust"] + 2.0:
        k = sstep(B["landbeat"] + 27.6, B["dust"], t)
        nb = int(0.5 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        wh = stft_filter(noise(nb, int(t * 1000) % 100000), lambda ts, f: logband(f, 4000 * np.exp(-ts * 3) + 500, 0.6)) * np.exp(-tb_ / 0.2)
        place(buf, t, wh, r.uniform(-1, 1), 0.2)
        t += (0.6 - 0.55 * k) * r.uniform(0.5, 1.5)
    # feet: a crowd of them, running over the leaf, then walking; shouts without words; the cat; the clash
    t = B["fill"]
    while t < B["rest"] + 2.0:
        run = 1 - sstep(B["fill"] + 1.5, B["fill"] + 3.0, t)
        stop = sstep(B["rest"], B["rest"] + 2, t)
        nb = int(0.08 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        thud = np.sin(2 * np.pi * 70 * tb_) * np.exp(-tb_ / 0.03) + noise(nb, int(t * 1000) % 100000) * np.exp(-tb_ / 0.01) * 0.3
        place(buf, t, thud, r.uniform(-0.5, 0.5), 0.35 * (1 - stop))
        t += (0.11 if run > 0.5 else 0.22) * r.uniform(0.6, 1.4)
    for _ in range(26):
        t = r.uniform(B["fill"] + 1.0, B["rest"] - 2)
        nb = int(r.uniform(0.25, 0.7) * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        f0 = r.uniform(140, 300)
        contour = f0 * (1 + 0.3 * np.sin(np.pi * tb_ / (nb / SR)))
        v = np.sin(2 * np.pi * np.cumsum(contour) / SR)
        v = stft_filter(v, lambda ts, f: logband(f, 700, 0.5) + 0.6 * logband(f, 1300, 0.4))
        v = v * np.sin(np.pi * tb_ / (nb / SR)) ** 0.5
        place(buf, t, v, r.uniform(-0.8, 0.8), 0.18)
    for t in (B["fill"] + 11.0, B["fill"] + 12.4):
        nb = int(0.7 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        snarl = stft_filter(noise(nb, 777), lambda ts, f: logband(f, 500, 0.7)) * (0.5 + 0.5 * np.sin(2 * np.pi * 28 * tb_)) * np.sin(np.pi * tb_ / 0.7)
        place(buf, t, snarl, 0.6, 0.45)
    for k in range(7):
        t = B["fill"] + 17.8 + k * 0.33
        nb = int(0.15 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        hit = noise(nb, 800 + k) * np.exp(-tb_ / 0.02) + np.sin(2 * np.pi * 120 * tb_) * np.exp(-tb_ / 0.05)
        place(buf, t, hit, r.uniform(-0.5, 0.5), 0.4)
    # birds over the river and the delta
    t = B["fill"] + 30
    while t < B["rest"] + 20:
        f0 = r.uniform(1800, 3500)
        nb = int(0.12 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        ch = np.sin(2 * np.pi * (f0 * (1 + 0.15 * np.sin(2 * np.pi * 30 * tb_))) * tb_) * np.sin(np.pi * tb_ / 0.12)
        place(buf, t, ch, r.uniform(-1, 1), 0.04)
        t += r.uniform(0.15, 0.9)
    # the flock lifting: wingbeats in their thousands, 278-286
    nb = int(8 * SR)
    tb_ = np.arange(nb, dtype=np.float32) / SR
    fl = stft_filter(noise(nb, 900), lambda ts, f: logband(f, 1200, 1.0)) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * tb_) ** 2) * np.sin(np.pi * tb_ / 8) ** 0.7
    place(buf, B["rest"] + 2, fl, -0.3, 0.3)
    # the breathing of the band at the cliff, and the one breath drawn in at the end
    t = B["rest"] + 1.5
    while t < B["rest"] + 16:
        nb = int(3.2 * SR)
        tb_ = np.arange(nb, dtype=np.float32) / SR
        br = stft_filter(noise(nb, int(t * 100) % 10000), lambda ts, f: logband(f, 600, 1.2)) * np.sin(np.pi * tb_ / 3.2) ** 2
        place(buf, t, br, r.uniform(-0.6, 0.6), 0.05)
        t += r.uniform(2.2, 3.4)
    nb = int(3.0 * SR)
    tb_ = np.arange(nb, dtype=np.float32) / SR
    inhale = stft_filter(noise(nb, 901), lambda ts, f: logband(f, 500 + 900 * ts / 3, 1.0)) * (np.minimum(tb_ / 2.4, 1.0) ** 1.5) * (1 - sstep(2.6, 3.0, 0) )
    inhale *= np.where(tb_ < 2.6, 1.0, np.clip(1 - (tb_ - 2.6) / 0.4, 0, 1))
    place(buf, B["rest"] + 18.5, inhale, 0.0, 0.5)
    return buf


def limiter(x, ceiling=0.97):
    return np.tanh(x * 1.2 / ceiling) * ceiling


def write_wav(path, x):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(x16.tobytes())


STEMS = [("hiss", stem_hiss), ("whisper", stem_whisper), ("release", stem_release), ("note", stem_note),
         ("atmos", stem_atmos), ("laugh", stem_laugh), ("grains", stem_grains), ("cosmos", stem_cosmos),
         ("world", stem_world)]

# mix levels: the release is the loudest thing in the sequence by a wide margin (treatment, beat 2)
GAINS = dict(hiss=1.8, whisper=1.8, release=1.0, note=0.55, atmos=0.5, laugh=0.6, grains=0.3, cosmos=0.45, world=0.3)

# v3: everything sits in one space. How much of each stem goes to the reverb; the release brings its
# own (stem_release, layer 6). The space is vast through the abstract beats and closes in from beat 10,
# when the world turns ordinary, to almost nothing at the cliff (open air, real time).
SENDS = dict(hiss=0.35, whisper=0.5, release=0.0, note=0.55, atmos=0.7, laugh=0.6, grains=0.7, cosmos=0.6, world=0.15)


def build(outdir, write_stems=True):
    os.makedirs(outdir, exist_ok=True)
    mix = np.zeros((N, 2), np.float32)
    send = np.zeros((N, 2), np.float32)
    for name, fn in STEMS:
        s = fn() * GAINS[name]
        if s.shape[0] != N:
            s = s[:N]
        print(f"stem {name:8s} peak {np.abs(s).max():.3f}", flush=True)
        if write_stems:
            write_wav(os.path.join(outdir, f"stem-{name}.wav"), s)
        mix += s
        send += s * SENDS[name]
    space_amt = env_curve([(0, 1.0), (B["swarm"], 1.0), (B["swarm"] + 4, 0.45), (B["rest"], 0.25), (DURATION, 0.15)])
    ir = reverb_ir(5.0, rt_low=4.5, rt_high=1.4, seed=99, predelay=0.035)
    wet = convolve(send * space_amt[:, None], ir)[:N] * 0.35
    print(f"stem {'space':8s} peak {np.abs(wet).max():.3f}", flush=True)
    if write_stems:
        write_wav(os.path.join(outdir, "stem-space.wav"), wet)
    mix += wet
    # the release is the loudest thing by a wide margin: everything else sits well under it
    mix = limiter(mix)
    write_wav(os.path.join(outdir, "mix.wav"), mix)
    print("mix peak", np.abs(mix).max())
    return os.path.join(outdir, "mix.wav")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "audio"
    build(out, write_stems="--no-stems" not in sys.argv)
