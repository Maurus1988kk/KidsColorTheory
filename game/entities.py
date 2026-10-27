"""Entità di gioco: particelle, gocce, pozioni e calderone.

Tutta la grafica è disegnata con primitive pygame. Le parti statiche vengono
precalcolate una volta (con antialiasing da supersampling) e poi solo blittate.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Optional

import pygame

from .color_mixing import RGB
from .constants import MAX_DOSES, Theme
from .ui import _rot, darken, draw_drop, lighten, supersample, text_surface


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# --- Particelle ---------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "gravity", "star")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, size: float,
                 color: RGB, gravity: float = 0.0, star: bool = False) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.star = star


class ParticleSystem:
    """Gestisce scintille, schizzi e scie. Niente alpha: le particelle rimpiccioliscono."""

    MAX_PARTICLES = 350

    def __init__(self) -> None:
        self.items: list[Particle] = []

    def add(self, p: Particle) -> None:
        if len(self.items) < self.MAX_PARTICLES:
            self.items.append(p)

    def clear(self) -> None:
        self.items.clear()

    def splash(self, x: float, y: float, color: RGB, n: int = 12) -> None:
        for _ in range(n):
            a = random.uniform(math.pi * 1.1, math.pi * 1.9)
            sp = random.uniform(120, 300)
            self.add(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.35, 0.7),
                              random.uniform(3, 6.5), lighten(color, random.uniform(0, 0.4)), gravity=900))

    def sparkles(self, x: float, y: float, n: int = 26) -> None:
        palette = [(255, 230, 80), (255, 255, 255), (255, 150, 220), (120, 230, 255), (170, 255, 140)]
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(80, 340)
            self.add(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp - 60, random.uniform(0.6, 1.2),
                              random.uniform(7, 14), random.choice(palette), gravity=220, star=True))

    def pour_drop(self, x: float, y: float, color: RGB) -> None:
        self.add(Particle(x, y, random.uniform(60, 160), random.uniform(0, 80), random.uniform(0.6, 0.9),
                          random.uniform(4, 8), color, gravity=1400))

    def update(self, dt: float) -> None:
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf: pygame.Surface) -> None:
        for p in self.items:
            r = max(1.0, p.size * (p.life / p.max_life))
            if p.star:
                pts = [(p.x, p.y - r), (p.x + r * 0.32, p.y - r * 0.32), (p.x + r, p.y),
                       (p.x + r * 0.32, p.y + r * 0.32), (p.x, p.y + r), (p.x - r * 0.32, p.y + r * 0.32),
                       (p.x - r, p.y), (p.x - r * 0.32, p.y - r * 0.32)]
                pygame.draw.polygon(surf, p.color, pts)
            else:
                pygame.draw.circle(surf, p.color, (p.x, p.y), r)


# --- Goccia -------------------------------------------------------------------
class Drop:
    """Goccia che cade dalla pozione al calderone, con una piccola scia."""

    GRAVITY = 2000.0

    def __init__(self, index: int, start: tuple[float, float], target_x: float, rim_y: float,
                 color: RGB, surface_y: Callable[[], float]) -> None:
        self.index = index
        self.x0, self.y0 = start
        self.x, self.y = start
        self.target_x = target_x
        self.rim_y = rim_y
        self.color = color
        self.surface_y = surface_y
        self.vy = 80.0
        self.trail: list[tuple[float, float]] = []

    def update(self, dt: float) -> bool:
        """Avanza la goccia; True quando tocca il liquido (o il fondo)."""
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)
        self.vy += self.GRAVITY * dt
        self.y += self.vy * dt
        # Spostamento orizzontale morbido verso l'imboccatura, poi caduta verticale.
        span = max(1.0, self.rim_y - self.y0)
        self.x = self.x0 + (self.target_x - self.x0) * smoothstep((self.y - self.y0) / span)
        return self.y >= self.surface_y()

    def draw(self, surf: pygame.Surface) -> None:
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            pygame.draw.circle(surf, self.color, (tx, ty), 3 + 7 * (i + 1) / (n + 1) * 0.8)
        draw_drop(surf, self.x, self.y, 11, self.color)
        pygame.draw.circle(surf, lighten(self.color, 0.7), (self.x - 4, self.y - 3), 3)


# --- Pozione ------------------------------------------------------------------
POTION_W, POTION_H = 150, 190


def _paint_flask(big: pygame.Surface, k: int, color: RGB) -> None:
    glass = (235, 245, 255)
    outline = (95, 120, 170)
    cx, cy, r = 75 * k, 120 * k, 64 * k
    # collo e corpo (vetro)
    pygame.draw.rect(big, glass, (58 * k, 14 * k, 34 * k, 70 * k))
    pygame.draw.circle(big, glass, (cx, cy), r)
    # liquido: cerchio ritagliato + parte nel collo
    clip = big.get_clip()
    big.set_clip(pygame.Rect(0, 78 * k, POTION_W * k, POTION_H * k))
    pygame.draw.circle(big, color, (cx, cy), r - 5 * k)
    big.set_clip(clip)
    pygame.draw.rect(big, color, (61 * k, 78 * k, 28 * k, 16 * k))
    pygame.draw.ellipse(big, lighten(color, 0.35), (62 * k, 73 * k, 26 * k, 10 * k))
    # contorni
    pygame.draw.circle(big, outline, (cx, cy), r, 5 * k)
    pygame.draw.line(big, outline, (58 * k, 14 * k), (58 * k, 62 * k), 5 * k)
    pygame.draw.line(big, outline, (92 * k, 14 * k), (92 * k, 62 * k), 5 * k)
    pygame.draw.rect(big, glass, (54 * k, 52 * k, 42 * k, 18 * k))  # copre l'attacco collo/corpo
    pygame.draw.rect(big, outline, (52 * k, 8 * k, 46 * k, 10 * k), border_radius=4 * k)
    # tappo di sughero
    pygame.draw.rect(big, (196, 140, 80), (57 * k, 0, 36 * k, 14 * k), border_radius=5 * k)
    pygame.draw.rect(big, (160, 105, 55), (57 * k, 0, 36 * k, 14 * k), 3 * k, border_radius=5 * k)
    # riflessi
    pygame.draw.arc(big, (255, 255, 255), (28 * k, 72 * k, 60 * k, 100 * k), math.radians(110), math.radians(175), 6 * k)
    pygame.draw.circle(big, (255, 255, 255), (44 * k, 158 * k), 4 * k)
    # faccina
    ink = (50, 35, 70)
    for ex in (57, 93):
        pygame.draw.ellipse(big, (255, 255, 255), ((ex - 9) * k, 95 * k, 18 * k, 22 * k))
        pygame.draw.circle(big, ink, (ex * k, 108 * k), 5 * k)
        pygame.draw.circle(big, (255, 255, 255), ((ex - 2) * k, 106 * k), 2 * k)
    pygame.draw.arc(big, ink, (62 * k, 112 * k, 26 * k, 20 * k), math.pi, math.tau, 4 * k)
    for cxk in (46, 104):
        pygame.draw.circle(big, lighten(color, 0.45), (cxk * k, 125 * k), 6 * k)


_flask_cache: dict[tuple[RGB, str], pygame.Surface] = {}


def flask_surface(color: RGB, label: str) -> pygame.Surface:
    key = (color, label)
    if key not in _flask_cache:
        surf = supersample((POTION_W, POTION_H), lambda big, k: _paint_flask(big, k, color), 3)
        # cartellino con il nome
        tag = pygame.Rect(0, 0, 84, 26)
        tag.center = (75, 152)
        pygame.draw.rect(surf, (255, 255, 255), tag, border_radius=10)
        pygame.draw.rect(surf, (95, 120, 170), tag, 2, border_radius=10)
        txt = text_surface(label, 19, (50, 35, 70))
        surf.blit(txt, txt.get_rect(center=tag.center))
        _flask_cache[key] = surf
    return _flask_cache[key]


class Potion:
    """Ampolla cliccabile con effetto hover (si ingrandisce) e rimbalzo al clic."""

    def __init__(self, index: int, center: tuple[int, int], color: RGB, label: str) -> None:
        self.index = index
        self.center = center
        self.color = color
        self.label = label
        self._scale = 1.0
        self._vel = 0.0
        self._shake = 0.0

    def set_look(self, color: RGB, label: str) -> None:
        self.color, self.label = color, label
        self.bounce()

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, POTION_W, POTION_H)
        r.center = self.center
        return r

    @property
    def drop_origin(self) -> tuple[float, float]:
        return (self.center[0], self.center[1] + POTION_H * 0.5 - 8)

    def hit(self, pos, padding: int) -> bool:
        return self.rect.inflate(padding * 2, padding * 2).collidepoint(pos)

    def bounce(self) -> None:
        self._vel -= 3.2  # "schiaccia" l'ampolla, poi la molla la fa rimbalzare

    def shake(self) -> None:
        self._shake = 1.0

    def update(self, dt: float, hovered: bool) -> None:
        target = 1.12 if hovered else 1.0
        # molla smorzata
        self._vel += ((target - self._scale) * 220 - self._vel * 14) * dt
        self._scale += self._vel * dt
        self._shake = max(0.0, self._shake - dt * 2.2)

    def draw(self, surf: pygame.Surface, t: float) -> None:
        base = flask_surface(self.color, self.label)
        angle = math.sin(t * 38) * 7 * self._shake
        if abs(self._scale - 1) < 0.004 and abs(angle) < 0.1:
            img = base
        else:
            img = pygame.transform.rotozoom(base, angle, self._scale)
        surf.blit(img, img.get_rect(center=self.center))


# --- Contatore a gocce ----------------------------------------------------------
_pip_cache: dict[tuple, pygame.Surface] = {}


def pip_surface(color: Optional[RGB], outline: RGB) -> pygame.Surface:
    key = (color, outline)
    if key not in _pip_cache:
        def paint(big: pygame.Surface, k: int) -> None:
            if color is not None:
                draw_drop(big, 8 * k, 20 * k, 6.5 * k, color)
            else:  # goccia vuota: solo il contorno
                tip = (8 * k, 7 * k)
                pts = [tip, (13.6 * k, 16 * k), (13.6 * k, 20 * k), (8 * k, 26.5 * k), (2.4 * k, 20 * k), (2.4 * k, 16 * k)]
                pygame.draw.polygon(big, outline, pts, 2 * k)
        _pip_cache[key] = supersample((16, 28), paint, 3)
    return _pip_cache[key]


def draw_dose_counter(surf: pygame.Surface, center_x: int, y: int, count: int, color: RGB, outline: RGB) -> None:
    """Fila di MAX_DOSES gocce: piene = dosi aggiunte, vuote = spazio libero."""
    full = pip_surface(color, outline)
    empty = pip_surface(None, outline)
    step = 15
    x0 = center_x - (MAX_DOSES * step) // 2
    for i in range(MAX_DOSES):
        surf.blit(full if i < count else empty, (x0 + i * step - 1, y))


# --- Calderone ----------------------------------------------------------------
LW, LH = 380, 290  # superficie locale del calderone
CX, CY, R = 190, 140, 130  # centro e raggio del corpo
RIM_Y = 60  # altezza (locale) del bordo / imboccatura
BOTTOM_Y = CY + R - 6
TOP_FULL_Y = RIM_Y + 14
POUR_TIME = 1.35


class Cauldron:
    """Calderone di vetro: mostra il liquido, le bolle, l'onda e l'animazione di svuotamento."""

    def __init__(self, center: tuple[int, int], theme: Theme, light_mode: bool) -> None:
        self.center = center  # posizione mondo del centro del cerchio (CX, CY locali)
        self.origin = (center[0] - CX, center[1] - CY)  # angolo in alto a sinistra
        self.light_mode = light_mode
        self.theme = theme
        self.color: RGB = (255, 255, 255)
        self._color_disp = [255.0, 255.0, 255.0]
        self.total = 0
        self.level = 0.0  # livello mostrato (0..1)
        self.slosh = 0.0
        self.shake_t = 0.0
        self.bubbles: list[list[float]] = []
        self.pouring = False
        self._pour_t = 0.0
        self._pour_level0 = 0.0
        self.tilt = 0.0  # gradi, in senso orario
        self._work = pygame.Surface((LW, LH), pygame.SRCALPHA)
        self._liq = pygame.Surface((LW, LH), pygame.SRCALPHA)
        self._build_static()

    # --- Precalcolo -------------------------------------------------------
    def _build_static(self) -> None:
        def paint_mask(big: pygame.Surface, k: int) -> None:
            pygame.draw.circle(big, (255, 255, 255, 255), (CX * k, CY * k), (R - 8) * k)
            pygame.draw.rect(big, (0, 0, 0, 0), (0, 0, LW * k, (RIM_Y + 6) * k))

        self._mask = supersample((LW, LH), paint_mask, 3)
        self._back = self._mask.copy()
        self._back.fill(self.theme.glass_inside + (255,), special_flags=pygame.BLEND_RGBA_MULT)

        def paint_front(big: pygame.Surface, k: int) -> None:
            ring = (110, 160, 215) if not self.light_mode else (150, 185, 255)
            pygame.draw.circle(big, ring, (CX * k, CY * k), R * k, 9 * k)
            pygame.draw.circle(big, (255, 255, 255), (CX * k, CY * k), (R - 12) * k, 3 * k)
            pygame.draw.rect(big, (0, 0, 0, 0), (0, 0, LW * k, (RIM_Y - 4) * k))
            # bordo (labbro) del calderone
            half = int(math.sqrt(R * R - (CY - RIM_Y) ** 2)) + 16
            lip = pygame.Rect((CX - half) * k, (RIM_Y - 14) * k, 2 * half * k, 24 * k)
            pygame.draw.rect(big, ring, lip, border_radius=12 * k)
            pygame.draw.rect(big, (255, 255, 255), lip.inflate(-10 * k, -14 * k).move(0, -2 * k), border_radius=6 * k)
            # riflessi sul vetro
            pygame.draw.arc(big, (255, 255, 255), ((CX - R + 22) * k, (CY - R + 30) * k, (2 * R - 44) * k, (2 * R - 44) * k),
                            math.radians(155), math.radians(215), 9 * k)
            pygame.draw.circle(big, (255, 255, 255), ((CX - 85) * k, (CY + 40) * k), 5 * k)

        self._front = supersample((LW, LH), paint_front, 3)

        def paint_shadow(big: pygame.Surface, k: int) -> None:
            pygame.draw.ellipse(big, (*self.theme.shadow, 70), (0, 0, 250 * k, 26 * k))

        self._shadow = supersample((250, 26), paint_shadow, 3)

        # alone luminoso (modalità luce): superficie RGB da sommare allo sfondo
        size = 420
        glow = pygame.Surface((size, size))
        for i in range(60, 0, -1):
            v = int(255 * (1 - i / 60) ** 2 * 0.65)
            pygame.draw.circle(glow, (v, v, v), (size // 2, size // 2), int(size / 2 * i / 60))
        self._glow = glow

    # --- Stato ------------------------------------------------------------
    @property
    def busy(self) -> bool:
        return self.pouring

    @property
    def mouth_x(self) -> float:
        return self.center[0]

    @property
    def rim_world_y(self) -> float:
        return self.origin[1] + RIM_Y

    def surface_world_y(self) -> float:
        """Altezza (mondo) del pelo del liquido: dove atterrano le gocce."""
        return self.origin[1] + BOTTOM_Y - (BOTTOM_Y - TOP_FULL_Y) * self.level

    def set_state(self, color: Optional[RGB], total: int) -> None:
        """Imposta colore e quantità di liquido (il valore mostrato si adegua con fluidità)."""
        if self.pouring:
            return
        self.total = total
        if color is not None:
            if self.level < 0.02:  # calderone (quasi) vuoto: niente dissolvenza dal colore vecchio
                self._color_disp = [float(c) for c in color]
            self.color = color

    def reset(self) -> None:
        """Svuota subito (cambio modalità)."""
        self.total = 0
        self.level = 0.0
        self.pouring = False
        self.tilt = 0.0
        self.bubbles.clear()

    def splash(self) -> None:
        self.slosh = min(1.0, self.slosh + 0.7)

    def shake(self) -> None:
        self.shake_t = 1.0

    def pour(self) -> bool:
        """Avvia l'animazione di svuotamento. False se non c'è nulla da svuotare."""
        if self.pouring or self.level < 0.02:
            return False
        self.pouring = True
        self._pour_t = 0.0
        self._pour_level0 = self.level
        self.total = 0
        return True

    def spout_world(self) -> Optional[tuple[float, float]]:
        """Punto da cui esce il liquido durante lo svuotamento (None se non esce nulla)."""
        if not self.pouring or self.tilt < 14 or self.level < 0.03:
            return None
        half = int(math.sqrt(R * R - (CY - RIM_Y) ** 2)) + 8
        x, y = _rot([(CX + half, RIM_Y - 2)], self.tilt, (CX, CY))[0]
        return (self.origin[0] + x, self.origin[1] + y)

    # --- Aggiornamento --------------------------------------------------------
    def update(self, dt: float) -> None:
        target = self.total / MAX_DOSES
        if self.pouring:
            self._pour_t += dt
            p = min(1.0, self._pour_t / POUR_TIME)
            self.tilt = 40 * smoothstep(p / 0.3) * (1 - smoothstep((p - 0.82) / 0.18))
            self.level = self._pour_level0 * (1 - smoothstep((p - 0.12) / 0.68))
            if p >= 1.0:
                self.pouring = False
                self.level = 0.0
                self.tilt = 0.0
        else:
            self.level += (target - self.level) * min(1.0, dt * 6)
            if abs(target - self.level) < 0.002:
                self.level = target
        # colore mostrato: interpolazione fluida verso il colore calcolato
        k = min(1.0, dt * 7)
        for i in range(3):
            self._color_disp[i] += (self.color[i] - self._color_disp[i]) * k
        self.slosh = max(0.0, self.slosh - dt * 1.6)
        self.shake_t = max(0.0, self.shake_t - dt * 1.8)
        self._update_bubbles(dt)

    def _update_bubbles(self, dt: float) -> None:
        surf_y = BOTTOM_Y - (BOTTOM_Y - TOP_FULL_Y) * self.level
        if self.level > 0.08 and not self.pouring and len(self.bubbles) < 14 and random.random() < dt * 5:
            r = random.uniform(3, 8)
            self.bubbles.append([CX + random.uniform(-70, 70), BOTTOM_Y - random.uniform(5, 40), r,
                                 random.uniform(35, 80), random.uniform(0, 6.28)])
        alive = []
        for b in self.bubbles:
            b[1] -= b[3] * dt
            if b[1] > surf_y + 6 and self.level > 0.02:
                alive.append(b)
        self.bubbles = alive

    # --- Disegno ----------------------------------------------------------------
    @property
    def liquid_rgb(self) -> RGB:
        return (int(self._color_disp[0]), int(self._color_disp[1]), int(self._color_disp[2]))

    def draw_glow(self, surf: pygame.Surface) -> None:
        if not self.light_mode or self.level < 0.03:
            return
        s = min(1.0, 0.35 + self.level)
        tint = tuple(int(c * s) for c in self.liquid_rgb)
        g = self._glow.copy()
        g.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(g, g.get_rect(center=(self.center[0], self.center[1] + 20)), special_flags=pygame.BLEND_RGB_ADD)

    def draw(self, surf: pygame.Surface, t: float) -> None:
        # ombra a terra (non ruota)
        surf.blit(self._shadow, self._shadow.get_rect(center=(self.center[0], self.origin[1] + CY + R + 4)))
        work = self._work
        work.fill((0, 0, 0, 0))
        work.blit(self._back, (0, 0))
        self._draw_liquid(t)
        work.blit(self._liq, (0, 0))
        work.blit(self._front, (0, 0))

        angle_cw = self.tilt + 5 * math.sin(t * 32) * self.shake_t ** 2
        if abs(angle_cw) < 0.05:
            surf.blit(work, self.origin)
        else:
            img = pygame.transform.rotozoom(work, -angle_cw, 1.0)
            # il perno è il centro del cerchio, non il centro della superficie
            off = _rot([(LW / 2, LH / 2)], angle_cw, (CX, CY))[0]
            surf.blit(img, img.get_rect(center=(self.origin[0] + off[0], self.origin[1] + off[1])))

    def _draw_liquid(self, t: float) -> None:
        liq = self._liq
        liq.fill((0, 0, 0, 0))
        if self.level > 0.004:
            color = self.liquid_rgb
            y0 = BOTTOM_Y - (BOTTOM_Y - TOP_FULL_Y) * self.level
            amp = 2.5 + 6 * self.slosh
            pts = [(x, y0 + amp * math.sin(t * 3.2 + x * 0.045)) for x in range(0, LW + 1, 10)]
            pygame.draw.polygon(liq, color, pts + [(LW, LH), (0, LH)])
            # fondo più scuro per dare profondità
            deep = max(y0 + 30, BOTTOM_Y - 70)
            pygame.draw.rect(liq, darken(color, 0.14), (0, deep, LW, LH - deep))
            pygame.draw.lines(liq, lighten(color, 0.45), False, pts, 5)
            edge = lighten(color, 0.55)
            for bx, by, br, _sp, ph in self.bubbles:
                x = bx + math.sin(t * 2 + ph) * 4
                pygame.draw.circle(liq, edge, (x, by), br, 2)
                pygame.draw.circle(liq, edge, (x - br * 0.35, by - br * 0.35), max(1, br * 0.25))
        liq.blit(self._mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
