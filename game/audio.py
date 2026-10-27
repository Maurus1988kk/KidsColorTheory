"""Effetti sonori sintetizzati da codice (nessun file audio) con fallback muto.

Se il dispositivo audio non è disponibile, `Audio` resta in modalità disattivata
e tutte le chiamate `play()` diventano no-op: il gioco continua senza suoni.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pygame


class Audio:
    def __init__(self) -> None:
        self.enabled = False
        self.muted = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._rate = 44100
        self._channels = 2
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            init = pygame.mixer.get_init()
            if init is None:
                return
            self._rate, _, self._channels = init
            self._build_sounds()
            self.enabled = True
        except Exception as exc:  # nessuna scheda audio, driver mancante, ecc.
            print(f"[audio] disattivato: {exc}")
            self.enabled = False
            self._sounds.clear()

    # --- API -----------------------------------------------------------
    def play(self, name: str, volume: float = 1.0) -> None:
        if not self.enabled or self.muted:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.set_volume(max(0.0, min(1.0, volume)))
                snd.play()
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted and self.enabled:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        return self.muted

    # --- Sintesi -------------------------------------------------------
    def _t(self, dur: float) -> np.ndarray:
        return np.linspace(0, dur, int(self._rate * dur), endpoint=False)

    def _sweep(self, f0: float, f1: float, dur: float, decay: float = 6.0) -> np.ndarray:
        """Sinusoide con glissando da f0 a f1 e inviluppo a decadimento."""
        t = self._t(dur)
        freq = f0 + (f1 - f0) * (t / dur)
        phase = 2 * np.pi * np.cumsum(freq) / self._rate
        env = np.exp(-decay * t / dur) * np.minimum(1.0, t / 0.004)  # attacco breve: niente "click"
        return np.sin(phase) * env

    def _note(self, freq: float, dur: float) -> np.ndarray:
        t = self._t(dur)
        env = np.exp(-5 * t / dur) * np.minimum(1.0, t / 0.005)
        return (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t)) * env * 0.7

    def _make(self, mono: np.ndarray, gain: float = 0.5) -> pygame.Sound:
        peak = float(np.max(np.abs(mono))) or 1.0
        data = (mono / peak * gain * 32767).astype(np.int16)
        if self._channels > 1:
            data = np.repeat(data[:, None], self._channels, axis=1)
        return pygame.sndarray.make_sound(np.ascontiguousarray(data))

    def _build_sounds(self) -> None:
        s = self._sounds
        # "blip" della goccia che parte: un fischietto acuto e brevissimo
        s["drop"] = self._make(self._sweep(900, 1500, 0.09, 5), 0.35)
        # "plop" quando la goccia cade: tre intonazioni, una per pozione
        rng = np.random.default_rng(7)
        for i, base in enumerate((392.0, 494.0, 587.0)):  # sol, si, re
            plop = self._sweep(base * 1.6, base * 0.7, 0.16, 7)
            noise = rng.standard_normal(len(plop)) * np.exp(-60 * self._t(0.16)) * 0.15
            s[f"plop{i}"] = self._make(plop + noise, 0.5)
        # "glug glug" dello svuotamento: oscillatore grave con vibrato
        t = self._t(0.8)
        freq = 170 + 70 * np.sin(2 * np.pi * 9 * t) - 60 * t
        glug = np.sin(2 * np.pi * np.cumsum(freq) / self._rate)
        glug *= np.exp(-1.5 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t)) * np.minimum(1.0, t / 0.01)
        s["glug"] = self._make(glug, 0.55)
        # jingle allegro (arpeggio do-mi-sol-do)
        notes = [self._note(f, 0.16) for f in (523.25, 659.25, 783.99, 1046.5)]
        jingle = np.zeros(int(self._rate * 0.16 * 3) + len(notes[-1]) + 2000)
        for i, n in enumerate(notes):
            start = int(i * 0.1 * self._rate)
            jingle[start:start + len(n)] += n
        s["jingle"] = self._make(jingle, 0.5)
        # "pieno": due note morbide discendenti (gentile, niente buzzer)
        full = np.concatenate([self._note(392.0, 0.12), self._note(330.0, 0.18)])
        s["full"] = self._make(full, 0.35)
        # click dei pulsanti
        s["click"] = self._make(self._sweep(700, 500, 0.05, 6), 0.3)


def create_audio() -> Audio:
    """Crea l'Audio senza mai sollevare eccezioni."""
    try:
        return Audio()
    except Exception:  # paracadute extra
        a: Optional[Audio] = Audio.__new__(Audio)
        a.enabled = False
        a.muted = False
        a._sounds = {}
        return a
