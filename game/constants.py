"""Costanti e configurazione del gioco (layout, tempi, temi grafici)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from .color_mixing import RGB, Mode

TITLE = "MixaPozioni"
LOGICAL_W, LOGICAL_H = 1024, 768  # superficie logica, poi scalata alla finestra
FPS = 60
MAX_DOSES = 10  # dosi totali massime nel calderone


def resource_path(relative: str) -> str:
    """Percorso di una risorsa, valido sia da sorgente sia dentro PyInstaller.

    Oggi il gioco non ha asset esterni (tutto è disegnato da codice), ma
    l'helper è pronto per l'eventuale aggiunta di file.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, relative)


# --- Layout (coordinate logiche) -----------------------------------------
POTION_CENTERS = [(212, 228), (512, 228), (812, 228)]
CAULDRON_CENTER = (512, 520)  # centro del cerchio del calderone
NAME_PANEL = (152, 668, 720, 84)  # x, y, w, h
EMPTY_BUTTON = (756, 470, 236, 110)
MODE_BUTTON_SIZE = (230, 72)
MODE_BUTTONS_Y = 14
SMALL_BUTTON = 72
MUTE_BUTTON_POS = (940, 14)
FULLSCREEN_BUTTON_POS = (858, 14)
HIT_PADDING = 22  # area di clic extra attorno alle pozioni


@dataclass(frozen=True)
class Theme:
    bg_top: RGB
    bg_bottom: RGB
    panel: RGB
    panel_border: RGB
    text: RGB
    glass_inside: RGB  # interno del calderone quando è vuoto
    shadow: RGB


THEMES: dict[Mode, Theme] = {
    Mode.PAINT: Theme(
        bg_top=(135, 206, 250),
        bg_bottom=(255, 238, 190),
        panel=(255, 255, 255),
        panel_border=(120, 90, 170),
        text=(64, 40, 96),
        glass_inside=(225, 240, 250),
        shadow=(70, 50, 100),
    ),
    Mode.LIGHT: Theme(
        bg_top=(8, 8, 32),
        bg_bottom=(48, 22, 90),
        panel=(36, 30, 72),
        panel_border=(150, 130, 230),
        text=(255, 255, 255),
        glass_inside=(14, 12, 28),
        shadow=(0, 0, 10),
    ),
}

# Colori dei pulsanti
BTN_PAINT = (255, 140, 60)
BTN_LIGHT = (255, 200, 40)
BTN_EMPTY = (70, 170, 240)
BTN_SOUND = (110, 200, 120)
BTN_FULLSCREEN = (170, 120, 230)
BTN_YES = (90, 200, 110)
BTN_NO = (240, 100, 100)
