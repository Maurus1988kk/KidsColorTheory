"""Smoke test headless: simula clic, cambio modalità, svuota; salva screenshot in docs/.

Uso:  python tools/smoke_test.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game import constants as C  # noqa: E402
from game.color_mixing import Mode  # noqa: E402
from game.game import Game  # noqa: E402

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")


def click(game: Game, pos) -> None:
    # coordinate logiche -> coordinate finestra (come farebbe il mouse reale)
    ox, oy = game._view_offset
    s = game._view_scale
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(int(ox + pos[0] * s), int(oy + pos[1] * s)), button=1))


def run(game: Game, seconds: float) -> None:
    for _ in range(int(seconds * 60)):
        game.step(1 / 60)


def main() -> None:
    os.makedirs(DOCS, exist_ok=True)
    g = Game()
    run(g, 0.3)
    p = C.POTION_CENTERS
    # Pittura: rosso + giallo -> arancione
    click(g, p[0]); run(g, 0.2); click(g, p[1]); run(g, 1.5)
    assert g.current_name == "Arancione", g.current_name
    g.save = lambda path: pygame.image.save(g.canvas, path)
    g.save(os.path.join(DOCS, "screenshot_pittura.png"))
    # calderone pieno: i clic extra non devono dare errori
    for _ in range(12):
        click(g, p[2]); run(g, 0.05)
    run(g, 1.5)
    assert g._doses_total() == C.MAX_DOSES, (g.counts, g.pending, g.cauldron.busy)
    # svuota
    click(g, pygame.Rect(*C.EMPTY_BUTTON).center); run(g, 0.7)
    g.save(os.path.join(DOCS, "screenshot_svuota.png"))
    run(g, 1.2)
    assert sum(g.counts) == 0 and not g.cauldron.busy
    # Luce: rosso + verde + blu -> bianco
    click(g, g.selector.buttons[Mode.LIGHT].rect.center); run(g, 0.3)
    assert g.mode is Mode.LIGHT
    for i in range(3):
        click(g, p[i]); run(g, 0.15)
    run(g, 1.5)
    assert g.current_name == "Bianco", g.current_name
    g.save(os.path.join(DOCS, "screenshot_luce.png"))
    # mute, ESC (conferma), ridimensionamento
    click(g, g.mute_btn.rect.center); run(g, 0.1)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0))
    run(g, 0.2)
    assert g.confirm_quit and g.running
    g.save(os.path.join(DOCS, "screenshot_conferma.png"))
    click(g, g.no_btn.rect.center); run(g, 0.1)
    assert not g.confirm_quit
    pygame.display.set_mode((500, 300), pygame.RESIZABLE)
    run(g, 0.2)
    click(g, g.selector.buttons[Mode.PAINT].rect.center); run(g, 0.2)
    pygame.quit()
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
