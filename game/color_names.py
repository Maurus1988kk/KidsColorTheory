"""Nomi italiani dei colori: si sceglie il nome più vicino al colore ottenuto.

La distanza è calcolata nello spazio CIE Lab (più vicino alla percezione umana
rispetto alla semplice distanza RGB). Funzioni pure, senza pygame.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from .color_mixing import RGB, Mode

EMPTY_NAME = "Aggiungi una pozione!"

# Tabelle (nome, colore di riferimento). Pensate per bambini: nomi semplici.
_PAINT_NAMES: list[tuple[str, RGB]] = [
    ("Rosso", (228, 38, 52)),
    ("Arancione", (255, 134, 14)),
    ("Giallo", (255, 214, 10)),
    ("Verde chiaro", (150, 205, 40)),
    ("Verde", (28, 168, 66)),
    ("Azzurro", (90, 190, 240)),
    ("Blu", (36, 92, 226)),
    ("Viola", (138, 42, 168)),
    ("Fucsia", (190, 40, 120)),
    ("Rosa", (255, 150, 190)),
    ("Marrone", (118, 72, 38)),
    ("Verde scuro", (30, 100, 55)),
]

_LIGHT_NAMES: list[tuple[str, RGB]] = [
    ("Rosso", (255, 0, 0)),
    ("Arancione", (255, 128, 0)),
    ("Giallo", (255, 255, 0)),
    ("Verde lime", (128, 255, 0)),
    ("Verde", (0, 255, 0)),
    ("Verde acqua", (0, 255, 128)),
    ("Ciano", (0, 255, 255)),
    ("Azzurro", (0, 128, 255)),
    ("Blu", (0, 0, 255)),
    ("Viola", (128, 0, 255)),
    ("Magenta", (255, 0, 255)),
    ("Rosa", (255, 0, 128)),
    ("Bianco", (255, 255, 255)),
]

NAME_TABLES: dict[Mode, list[tuple[str, RGB]]] = {
    Mode.PAINT: _PAINT_NAMES,
    Mode.LIGHT: _LIGHT_NAMES,
}


def _srgb_to_lab(rgb: RGB) -> tuple[float, float, float]:
    """Conversione sRGB (0-255) -> CIE Lab (illuminante D65)."""

    def lin(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


@lru_cache(maxsize=None)
def _table_lab(mode: Mode) -> list[tuple[str, tuple[float, float, float]]]:
    return [(name, _srgb_to_lab(rgb)) for name, rgb in NAME_TABLES[mode]]


def color_name(mode: Mode, rgb: Optional[RGB]) -> str:
    """Nome italiano del colore più vicino; EMPTY_NAME se il calderone è vuoto."""
    if rgb is None:
        return EMPTY_NAME
    lab = _srgb_to_lab(rgb)
    best_name, best_dist = EMPTY_NAME, float("inf")
    for name, ref in _table_lab(mode):
        dist = (lab[0] - ref[0]) ** 2 + (lab[1] - ref[1]) ** 2 + (lab[2] - ref[2]) ** 2
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name
