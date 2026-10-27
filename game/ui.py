"""Elementi di interfaccia: font, icone disegnate a mano, pulsanti, selettore."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable, Optional

import pygame

from .color_mixing import RGB, Mode

# --- Font ------------------------------------------------------------------
# Font di sistema leggibili e "amichevoli", in ordine di preferenza. Se nessuno
# è presente si usa il font incluso in pygame (sempre disponibile).
_FONT_CANDIDATES = (
    "comicsansms", "trebuchetms", "verdana", "segoeui", "arialrounded",
    "dejavusans", "arial", "helvetica",
)
_font_path: Optional[str] = None
_font_path_resolved = False


def _resolve_font_path() -> Optional[str]:
    global _font_path, _font_path_resolved
    if not _font_path_resolved:
        _font_path_resolved = True
        for name in _FONT_CANDIDATES:
            try:
                path = pygame.font.match_font(name, bold=True)
            except Exception:
                path = None
            if path:
                _font_path = path
                break
    return _font_path


@lru_cache(maxsize=64)
def get_font(size: int) -> pygame.font.Font:
    path = _resolve_font_path()
    if path:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    return pygame.font.Font(None, int(size * 1.15))


@lru_cache(maxsize=256)
def text_surface(text: str, size: int, color: RGB) -> pygame.Surface:
    """Testo renderizzato (con cache: il rendering dei font è costoso)."""
    return get_font(size).render(text, True, color)


# --- Colori e primitive ----------------------------------------------------
def lighten(c: RGB, f: float) -> RGB:
    return (int(c[0] + (255 - c[0]) * f), int(c[1] + (255 - c[1]) * f), int(c[2] + (255 - c[2]) * f))


def darken(c: RGB, f: float) -> RGB:
    return (int(c[0] * (1 - f)), int(c[1] * (1 - f)), int(c[2] * (1 - f)))


def lerp_color(a: tuple, b: tuple, t: float) -> RGB:
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def draw_rounded(surf: pygame.Surface, rect: pygame.Rect, color: RGB, radius: int = 24,
                 border: int = 0, border_color: RGB = (255, 255, 255)) -> None:
    if border:
        pygame.draw.rect(surf, border_color, rect, border_radius=radius)
        inner = rect.inflate(-2 * border, -2 * border)
        pygame.draw.rect(surf, color, inner, border_radius=max(1, radius - border))
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)


def draw_drop(surf: pygame.Surface, cx: float, cy: float, r: float, color: RGB,
              outline: Optional[RGB] = None) -> None:
    """Goccia stilizzata: cerchio + punta in alto. (cx, cy) = centro del cerchio."""
    tip = (cx, cy - r * 2.0)
    dx = r * 0.86
    pts = [tip, (cx + dx, cy - r * 0.5), (cx - dx, cy - r * 0.5)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.circle(surf, color, (cx, cy), r)
    if outline:
        pygame.draw.circle(surf, outline, (cx, cy), r, 2)


def supersample(size: tuple[int, int], painter: Callable[[pygame.Surface, int], None],
                k: int = 3) -> pygame.Surface:
    """Disegna a risoluzione k volte maggiore e riduce: bordi morbidi (antialiasing).

    Serve solo per superfici precalcolate (una volta sola), quindi il costo è
    irrilevante a runtime.
    """
    big = pygame.Surface((size[0] * k, size[1] * k), pygame.SRCALPHA)
    painter(big, k)
    return pygame.transform.smoothscale(big, size)


# --- Icone -----------------------------------------------------------------
# Ogni icona è disegnata in un quadrato di lato s centrato in (cx, cy).
def _rot(points, angle_deg: float, origin) -> list[tuple[float, float]]:
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for x, y in points:
        dx, dy = x - origin[0], y - origin[1]
        out.append((origin[0] + dx * ca - dy * sa, origin[1] + dx * sa + dy * ca))
    return out


def icon_brush(surf, cx, cy, s, _color=None) -> None:
    u = s / 100.0
    o = (cx, cy)
    # manico
    handle = [(cx - 7 * u, cy - 48 * u), (cx + 7 * u, cy - 48 * u), (cx + 5 * u, cy + 8 * u), (cx - 5 * u, cy + 8 * u)]
    pygame.draw.polygon(surf, (150, 95, 50), _rot(handle, 40, o))
    # ghiera metallica
    ferr = [(cx - 8 * u, cy + 6 * u), (cx + 8 * u, cy + 6 * u), (cx + 8 * u, cy + 26 * u), (cx - 8 * u, cy + 26 * u)]
    pygame.draw.polygon(surf, (190, 195, 205), _rot(ferr, 40, o))
    # setole con goccia di colore
    tip = _rot([(cx, cy + 50 * u)], 40, o)[0]
    base = _rot([(cx, cy + 26 * u)], 40, o)[0]
    pygame.draw.circle(surf, (230, 50, 90), tip, 14 * u)
    pygame.draw.circle(surf, (230, 50, 90), ((tip[0] + base[0]) / 2, (tip[1] + base[1]) / 2), 14 * u)
    pygame.draw.circle(surf, (255, 150, 180), (tip[0] - 4 * u, tip[1] - 4 * u), 4 * u)


def icon_bulb(surf, cx, cy, s, _color=None) -> None:
    u = s / 100.0
    # raggi
    for ang in range(-60, 61, 30):
        a = math.radians(ang - 90)
        p1 = (cx + math.cos(a) * 46 * u, cy - 8 * u + math.sin(a) * 46 * u)
        p2 = (cx + math.cos(a) * 60 * u, cy - 8 * u + math.sin(a) * 60 * u)
        pygame.draw.line(surf, (255, 255, 255), p1, p2, max(2, int(5 * u)))
    pygame.draw.circle(surf, (255, 241, 118), (cx, cy - 8 * u), 34 * u)
    pygame.draw.circle(surf, (255, 255, 220), (cx - 10 * u, cy - 18 * u), 9 * u)
    pygame.draw.rect(surf, (160, 160, 175), (cx - 16 * u, cy + 22 * u, 32 * u, 10 * u), border_radius=3)
    pygame.draw.rect(surf, (130, 130, 145), (cx - 12 * u, cy + 33 * u, 24 * u, 9 * u), border_radius=4)


def icon_bucket(surf, cx, cy, s, _color=None) -> None:
    """Secchio rovesciato con liquido che scende."""
    u = s / 100.0
    o = (cx - 5 * u, cy - 5 * u)
    body = [(cx - 30 * u, cy - 28 * u), (cx + 30 * u, cy - 28 * u), (cx + 22 * u, cy + 24 * u), (cx - 22 * u, cy + 24 * u)]
    body = _rot(body, -55, o)
    rim = _rot([(cx - 32 * u, cy - 34 * u), (cx + 32 * u, cy - 34 * u), (cx + 32 * u, cy - 24 * u), (cx - 32 * u, cy - 24 * u)], -55, o)
    pygame.draw.polygon(surf, (255, 255, 255), body)
    pygame.draw.polygon(surf, (200, 225, 250), body, max(2, int(4 * u)))
    pygame.draw.polygon(surf, (225, 240, 255), rim)
    # getto + gocce
    mouth = _rot([(cx - 6 * u, cy - 26 * u)], -55, o)[0]
    pygame.draw.line(surf, (255, 255, 255), (mouth[0] - 2 * u, mouth[1]), (mouth[0] - 6 * u, mouth[1] + 36 * u), max(3, int(8 * u)))
    draw_drop(surf, mouth[0] - 8 * u, mouth[1] + 46 * u, 7 * u, (255, 255, 255))


def icon_sound(surf, cx, cy, s, muted: bool = False) -> None:
    u = s / 100.0
    white = (255, 255, 255)
    pygame.draw.polygon(surf, white, [
        (cx - 38 * u, cy - 14 * u), (cx - 20 * u, cy - 14 * u), (cx + 2 * u, cy - 36 * u),
        (cx + 2 * u, cy + 36 * u), (cx - 20 * u, cy + 14 * u), (cx - 38 * u, cy + 14 * u)])
    if muted:
        pygame.draw.line(surf, (235, 60, 60), (cx + 14 * u, cy - 22 * u), (cx + 44 * u, cy + 22 * u), max(3, int(9 * u)))
        pygame.draw.line(surf, (235, 60, 60), (cx + 14 * u, cy + 22 * u), (cx + 44 * u, cy - 22 * u), max(3, int(9 * u)))
    else:
        for r in (18, 32):
            rect = pygame.Rect(0, 0, r * 2 * u, r * 2 * u)
            rect.center = (cx + 4 * u, cy)
            pygame.draw.arc(surf, white, rect, -0.9, 0.9, max(3, int(7 * u)))


def icon_fullscreen(surf, cx, cy, s, _color=None) -> None:
    u = s / 100.0
    w = max(3, int(9 * u))
    a, b = 38 * u, 16 * u
    for sx in (-1, 1):
        for sy in (-1, 1):
            corner = (cx + sx * a, cy + sy * a)
            pygame.draw.line(surf, (255, 255, 255), corner, (corner[0] - sx * b * 1.6, corner[1]), w)
            pygame.draw.line(surf, (255, 255, 255), corner, (corner[0], corner[1] - sy * b * 1.6), w)


# --- Pulsante --------------------------------------------------------------
class Button:
    """Pulsante grande, arrotondato, con ombra, icona e/o etichetta.

    L'hover lo ingrandisce leggermente; il clic lo "schiaccia" per un attimo.
    """

    def __init__(self, rect: pygame.Rect, color: RGB, icon: Optional[Callable] = None,
                 label: str = "", font_size: int = 36, text_color: RGB = (255, 255, 255),
                 hit_padding: int = 8) -> None:
        self.rect = pygame.Rect(rect)
        self.color = color
        self.icon = icon
        self.label = label
        self.font_size = font_size
        self.text_color = text_color
        self.hit_padding = hit_padding
        self.active = False  # per i pulsanti "a selezione" (modalità)
        self.dimmed = False
        self.icon_args: tuple = ()
        self._scale = 1.0
        self._press = 0.0

    def hit(self, pos: tuple[float, float]) -> bool:
        return self.rect.inflate(self.hit_padding * 2, self.hit_padding * 2).collidepoint(pos)

    def press(self) -> None:
        self._press = 1.0

    def update(self, dt: float, mouse: tuple[float, float]) -> None:
        target = 1.06 if self.hit(mouse) else 1.0
        self._scale += (target - self._scale) * min(1.0, dt * 14)
        self._press = max(0.0, self._press - dt * 5)

    def draw(self, surf: pygame.Surface, shadow: RGB = (60, 40, 90)) -> None:
        sc = self._scale - 0.07 * math.sin(self._press * math.pi)
        r = self.rect.copy()
        r.width = int(self.rect.width * sc)
        r.height = int(self.rect.height * sc)
        r.center = self.rect.center
        base = darken(self.color, 0.35) if self.dimmed else self.color
        radius = min(r.height // 2, 30)
        # ombra + corpo + riflesso superiore
        draw_rounded(surf, r.move(0, 6), shadow, radius)
        border_col = (255, 255, 255) if self.active else darken(base, 0.25)
        draw_rounded(surf, r, base, radius, border=5 if self.active else 3, border_color=border_col)
        shine = pygame.Rect(r.x + 14, r.y + 8, r.width - 28, max(6, r.height // 5))
        draw_rounded(surf, shine, lighten(base, 0.3), shine.height // 2)
        # contenuto: icona (a sinistra se c'è anche testo) + etichetta
        cy = r.centery + 2
        icon_size = int(r.height * 0.78)
        if self.label:
            txt = text_surface(self.label, self.font_size, self.text_color)
            total = txt.get_width() + (icon_size + 8 if self.icon else 0)
            x = r.centerx - total // 2
            if self.icon:
                self.icon(surf, x + icon_size // 2, cy, icon_size, *self.icon_args)
                x += icon_size + 8
            surf.blit(txt, (x, cy - txt.get_height() // 2))
        elif self.icon:
            self.icon(surf, r.centerx, cy, icon_size, *self.icon_args)


class ModeSelector:
    """Due pulsanti grandi "Pittura" / "Luce"; uno solo è attivo."""

    def __init__(self, x: int, y: int, size: tuple[int, int], gap: int = 20) -> None:
        from .constants import BTN_LIGHT, BTN_PAINT  # import locale: evita dipendenze circolari

        self.mode = Mode.PAINT
        self.buttons: dict[Mode, Button] = {
            Mode.PAINT: Button(pygame.Rect(x, y, *size), BTN_PAINT, icon_brush, "Pittura", 38),
            Mode.LIGHT: Button(pygame.Rect(x + size[0] + gap, y, *size), BTN_LIGHT, icon_bulb, "Luce", 38,
                               text_color=(90, 60, 0)),
        }
        self._refresh()

    def _refresh(self) -> None:
        for m, b in self.buttons.items():
            b.active = m is self.mode
            b.dimmed = m is not self.mode

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        self._refresh()

    def hit(self, pos) -> Optional[Mode]:
        for m, b in self.buttons.items():
            if b.hit(pos):
                return m
        return None

    def update(self, dt: float, mouse) -> None:
        for b in self.buttons.values():
            b.update(dt, mouse)

    def draw(self, surf: pygame.Surface, shadow: RGB) -> None:
        for b in self.buttons.values():
            b.draw(surf, shadow)
