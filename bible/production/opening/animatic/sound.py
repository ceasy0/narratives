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


def tone(f_curve, amp_curve, harmonics=((1, 1.0), (2, 0.35), (3, 0.15), (4, 0.06)), vib=0.004):
    """A sustained tone whose pitch and level are curves over the whole duration."""
    ph = np.cumsum(f_curve) / SR
    vibr = 1 + vib * np.sin(2 * np.pi * 4.7 * T)
    out = np.zeros(N, np.float32)
    for h, a in harmonics:
        out += a * np.sin(2 * np.pi * h * ph * vibr)
    return out * amp_curve


def lowpass_env(x, cutoff_fn):
    return stft_filter(x, lambda t, f: (1 / (1 + (f / cutoff_fn(t)) ** 4)).astype(np.float32))


# ------------------------------------------------------------------------- the stems

def stem_hiss():
    """Wind over open water; from 16 s it narrows and climbs, like a breath drawn in that doesn't stop."""
    x = noise(N, 1)
    y = noise(N, 2)

    def gain(t, f):
        climb = sstep(16.0, 28.0, t)
        centre = 700 * (2 ** (climb * 2.6))  # up to about 4.2 kHz
        width = 2.2 - 1.6 * climb
        g = logband(f, centre, width) * (f > 60)
        # gusts
        g *= 0.8 + 0.2 * np.sin(t * 0.35) * np.sin(t * 0.11 + 1)
        return g

    # the hiss lives in beats 1-2; after the release it's gone except where the laugh and the serpent's
    # kin bring it back; here only beat 1 and the laugh pulses (stem_laugh) use it.
    L = stft_filter(x, gain)
    R = stft_filter(y, gain)
    level = env_curve([(0, 0.0), (1.5, 1.0), (16, 1.0), (27.9, 1.0 * db(10)), (28.0, 0.0), (DURATION, 0.0)])
    out = np.stack([L, R], axis=1) * level[:, None] * 0.05
    return out


def stem_whisper():
    """The same noise shaped like breath passing through an open mouth and throat: formants, no voice."""
    x = noise(N, 3)

    def gain(t, f):
        climb = sstep(16.0, 28.0, t)
        g = np.zeros_like(f)
        for fc, bw, a in ((520, 0.25, 1.0), (1500, 0.2, 0.7), (2500, 0.18, 0.45)):
            g += a * logband(f, fc * (1 + 0.8 * climb), bw)
        breath = 0.55 + 0.45 * np.sin(2 * np.pi * t / 4.5 - 1.2)  # slow breathing
        return g * (0.3 + 0.7 * breath)

    w = stft_filter(x, gain)
    level = env_curve([(0, 0), (5.5, 0), (10, 0.5), (17, 1.0), (27.9, 1.0 * db(6)), (28.0, 0), (DURATION, 0)])
    return np.stack([w, w], axis=1) * level[:, None] * 0.09


def stem_release():
    """The release at 0:28: a distorted sub-bass hit with real weight, and a tail that is the static
    itself, pitched and smeared, passing the ears and shutting behind the head. Then true silence."""
    buf = np.zeros((N, 2), np.float32)
    n = int(2.2 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 62 * np.exp(-t / 0.45) + 26
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) * np.exp(-t / 0.9)
    body = np.tanh(body * 4.0) * 0.95
    click = noise(int(0.012 * SR), 4) * np.linspace(1, 0, int(0.012 * SR))
    body[:len(click)] += click * 0.5
    place(buf, B["light"], body, 0.0, 1.0)
    # the tail: the hiss itself swept downward, widening, then shut
    nt = int(1.9 * SR)
    tail_src = noise(nt, 5)
    tt = np.arange(nt, dtype=np.float32) / SR

    def gain(tsec, fr):
        k = min(tsec / 1.6, 1.0)
        centre = 5000 * (2 ** (-k * 4.2))
        return logband(fr, centre, 0.9) * (1 - k) ** 1.5

    tail = stft_filter(tail_src, gain)
    tail *= np.exp(-tt / 0.7)
    # stereo: the two ears get it a few ms apart and opposite in phase, so it passes and shuts
    d = int(0.004 * SR)
    L = tail
    R = -np.concatenate([np.zeros(d, np.float32), tail[:-d]])
    place(buf[:, :1].reshape(-1, 1) if False else buf, B["light"], L, -1.0, 0.9)
    place(buf, B["light"], R, 1.0, 0.9)
    return buf


def stem_note():
    """One held note that belongs to whatever we're watching, from the eyes opening to the cliff."""
    # pitch by beat (Hz): faces A2, the grain up an octave, the proton a third voice, the atom higher,
    # the photon very high and pure, then down with the world: cell E4, animal A3, people E3, the face A2.
    f = env_curve([
        (0, 110), (B["sep"], 110), (B["eve"], 110), (B["eve"] + 10, 165), (B["vault"], 220),
        (B["land"] + 3, 220), (B["earth"], 196), (B["lights"], 196), (B["lights"] + 12, 247), (B["cross"] - 1, 880),
        (B["cross"], 880), (B["swarm"], 330), (B["landbeat"], 220), (B["dust"], 196), (B["fill"], 165),
        (B["rest"], 110), (DURATION, 110)])
    amp = env_curve([
        (0, 0), (34.5, 0), (35.5, 0.12), (B["sep"] + 12, 0.16), (B["sep"] + 13, 0.10), (B["eve"], 0.10),
        (B["vault"], 0.16), (B["cross"], 0.22), (B["cross"] + 6, 0.16), (B["swarm"], 0.14), (B["fill"], 0.10),
        (B["rest"], 0.10), (B["rest"] + 17, 0.10), (B["rest"] + 22, 0.0), (DURATION, 0)])
    # the timbre: purer for the photon, warmer for the faces and people
    purity = env_curve([(0, 0.3), (B["lights"] + 12, 0.3), (B["cross"], 1.0), (B["swarm"], 0.4), (DURATION, 0.3)])
    base = tone(f, amp, harmonics=((1, 1.0),), vib=0.003)
    warm = tone(f, amp, harmonics=((1, 0.0), (2, 0.35), (3, 0.18), (4, 0.08), (5, 0.04)), vib=0.003)
    out = base + warm * (1 - purity)
    # the proton: two more voices lock in at 94-99 s (a fifth and an octave), and stay through the atom
    k = env_curve([(0, 0), (B["land"] + 2.5, 0), (B["land"] + 5, 1), (B["earth"] + 6, 1), (B["lights"] + 10, 0), (DURATION, 0)])
    out += tone(f * 1.5, amp * 0.6 * k, harmonics=((1, 1.0), (2, 0.2)), vib=0.004)
    out += tone(f * 2.0, amp * 0.4 * k, harmonics=((1, 1.0),), vib=0.005)
    return np.stack([out, out], axis=1)


def stem_laugh():
    """The laugh carried by the hiss: hard pulses in the rhythm of laughter, no voice. 42-48 s. Then,
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
    # the electron: a high ping each orbit from 101 s, fading as the glare clears
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
    for i in range(len(W["ignite"])):
        t0 = B["lights"] + float(W["ignite"][i])
        n = int(0.6 * SR)
        tt = np.arange(n, dtype=np.float32) / SR
        src = noise(n, 200 + i)
        x = stft_filter(src, lambda ts, f: logband(f, 6000 * np.exp(-ts * 2.5) + 800, 0.7))
        x = x * np.exp(-tt / 0.18)
        pan = float(np.clip(W["pts"][i][0] / 2.0, -1, 1))
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
    # the flock lifting: wingbeats in their thousands, 268-276
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
         ("laugh", stem_laugh), ("grains", stem_grains), ("cosmos", stem_cosmos), ("world", stem_world)]

# mix levels: the release is the loudest thing in the sequence by a wide margin (treatment, beat 2)
GAINS = dict(hiss=1.0, whisper=1.0, release=1.0, note=0.6, laugh=0.6, grains=0.3, cosmos=0.45, world=0.3)


def build(outdir, write_stems=True):
    os.makedirs(outdir, exist_ok=True)
    mix = np.zeros((N, 2), np.float32)
    for name, fn in STEMS:
        s = fn() * GAINS[name]
        if s.shape[0] != N:
            s = s[:N]
        print(f"stem {name:8s} peak {np.abs(s).max():.3f}", flush=True)
        if write_stems:
            write_wav(os.path.join(outdir, f"stem-{name}.wav"), s)
        mix += s
    # the release is the loudest thing by a wide margin: everything else sits well under it
    mix = limiter(mix)
    write_wav(os.path.join(outdir, "mix.wav"), mix)
    print("mix peak", np.abs(mix).max())
    return os.path.join(outdir, "mix.wav")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "audio"
    build(out, write_stems="--no-stems" not in sys.argv)
