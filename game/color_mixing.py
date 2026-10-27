"""Miscelazione dei colori: funzioni pure, senza dipendenze da pygame.

Due modelli:
* PITTURA (sottrattivo, "quello della scuola"): primari Rosso, Giallo, Blu.
  Si usa il modello RYB con interpolazione trilineare sugli 8 vertici del cubo.
* LUCE (additivo, schermo): primari Rosso, Verde, Blu. Miscela additiva RGB.

In entrambi i casi l'input sono le DOSI (interi) dei tre primari, nell'ordine
in cui compaiono in PRIMARIES[mode]. Il risultato dipende solo dalle
PROPORZIONI: 1 rosso + 1 giallo dà lo stesso arancione di 4 rossi + 4 gialli.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Sequence

RGB = tuple[int, int, int]


class Mode(Enum):
    """Modalità colore del gioco."""

    PAINT = "pittura"
    LIGHT = "luce"


# Colori dei tre primari (usati sia per le pozioni sia come vertici del mixing).
PRIMARIES: dict[Mode, tuple[RGB, RGB, RGB]] = {
    Mode.PAINT: ((228, 38, 52), (255, 214, 10), (36, 92, 226)),  # R, Y, B
    Mode.LIGHT: ((255, 0, 0), (0, 255, 0), (0, 0, 255)),  # R, G, B
}

PRIMARY_LABELS: dict[Mode, tuple[str, str, str]] = {
    Mode.PAINT: ("Rosso", "Giallo", "Blu"),
    Mode.LIGHT: ("Rosso", "Verde", "Blu"),
}

# Vertici del cubo RYB -> RGB, indicizzati da (r, y, b) in {0, 1}.
# Derivati dal cubo classico di Gosset-Chen, ma con colori più vivaci:
# per dei bambini il verde deve sembrare verde, non "verde bottiglia".
_RYB_CORNERS: dict[tuple[int, int, int], RGB] = {
    (0, 0, 0): (255, 255, 255),  # nessun pigmento: bianco carta
    (1, 0, 0): PRIMARIES[Mode.PAINT][0],  # rosso
    (0, 1, 0): PRIMARIES[Mode.PAINT][1],  # giallo
    (0, 0, 1): PRIMARIES[Mode.PAINT][2],  # blu
    (1, 1, 0): (255, 134, 14),  # rosso + giallo = arancione
    (0, 1, 1): (28, 168, 66),  # giallo + blu = verde
    (1, 0, 1): (138, 42, 168),  # rosso + blu = viola
    (1, 1, 1): (118, 72, 38),  # tutti e tre = marrone
}


def _proportions(counts: Sequence[int]) -> Optional[tuple[float, float, float]]:
    """Normalizza le dosi dividendo per la più grande (il massimo diventa 1).

    Così il colore è sempre "pieno" (saturo): 1R+1Y vale (1, 1, 0) e non
    (0.5, 0.5, 0), che nel cubo darebbe un arancione slavato per via del bianco.
    Restituisce None se non c'è nessuna dose.
    """
    if len(counts) != 3:
        raise ValueError("Servono esattamente 3 quantità (una per primario)")
    values = [max(0, int(c)) for c in counts]
    peak = max(values)
    if peak == 0:
        return None
    return (values[0] / peak, values[1] / peak, values[2] / peak)


def mix_paint(counts: Sequence[int]) -> Optional[RGB]:
    """Pittura: dosi (rosso, giallo, blu) -> RGB, oppure None se vuoto."""
    prop = _proportions(counts)
    if prop is None:
        return None
    r, y, b = prop
    out = [0.0, 0.0, 0.0]
    # Interpolazione trilineare: ogni vertice pesa quanto la sua "vicinanza".
    for (cr, cy, cb), rgb in _RYB_CORNERS.items():
        w = (r if cr else 1 - r) * (y if cy else 1 - y) * (b if cb else 1 - b)
        if w:
            out[0] += rgb[0] * w
            out[1] += rgb[1] * w
            out[2] += rgb[2] * w
    return (round(out[0]), round(out[1]), round(out[2]))


def mix_light(counts: Sequence[int]) -> Optional[RGB]:
    """Luce: dosi (rosso, verde, blu) -> RGB additivo, oppure None se vuoto."""
    prop = _proportions(counts)
    if prop is None:
        return None
    return (round(255 * prop[0]), round(255 * prop[1]), round(255 * prop[2]))


def mix(mode: Mode, counts: Sequence[int]) -> Optional[RGB]:
    """Mescola le dosi secondo la modalità scelta."""
    if mode is Mode.PAINT:
        return mix_paint(counts)
    return mix_light(counts)


def kinds(counts: Sequence[int]) -> int:
    """Quanti primari diversi sono stati usati (>= 2 significa colore mescolato)."""
    return sum(1 for c in counts if c > 0)
