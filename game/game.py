"""Ciclo principale, stati, scaling della finestra e logica del gioco."""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from . import constants as C
from .audio import create_audio
from .color_mixing import PRIMARIES, PRIMARY_LABELS, Mode, kinds, mix
from .color_names import EMPTY_NAME, color_name
from .entities import (Cauldron, Drop, ParticleSystem, Potion, draw_dose_counter, smoothstep)
from .ui import (Button, ModeSelector, draw_rounded, icon_bucket, icon_bulb, icon_fullscreen,
                 icon_sound, lerp_color, text_surface)


def _build_background(theme: C.Theme) -> pygame.Surface:
    """Sfondo a gradiente verticale, precalcolato una sola volta."""
    bg = pygame.Surface((C.LOGICAL_W, C.LOGICAL_H))
    for y in range(C.LOGICAL_H):
        pygame.draw.line(bg, lerp_color(theme.bg_top, theme.bg_bottom, y / C.LOGICAL_H), (0, y), (C.LOGICAL_W, y))
    return bg


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        self.fullscreen = False
        self._windowed_size = self._initial_window_size()
        self.screen = pygame.display.set_mode(self._windowed_size, pygame.RESIZABLE)
        self.canvas = pygame.Surface((C.LOGICAL_W, C.LOGICAL_H)).convert()
        self.clock = pygame.time.Clock()
        self.audio = create_audio()
        self.running = True
        self.t = 0.0
        self._view_scale = 1.0
        self._view_offset = (0, 0)

        # Sfondi e calderoni per entrambe le modalità (precalcolati all'avvio)
        self.backgrounds = {m: _build_background(C.THEMES[m]) for m in Mode}
        self.cauldrons = {m: Cauldron(C.CAULDRON_CENTER, C.THEMES[m], m is Mode.LIGHT) for m in Mode}
        rng = random.Random(3)
        self.stars = [(rng.randrange(C.LOGICAL_W), rng.randrange(C.LOGICAL_H), rng.uniform(0, 6.28), rng.choice((1, 2, 2, 3)))
                      for _ in range(70)]
        self.clouds = [(rng.randrange(C.LOGICAL_W), rng.randrange(380, 740), rng.randrange(40, 110)) for _ in range(7)]

        self.mode = Mode.PAINT
        self.potions = [Potion(i, C.POTION_CENTERS[i], PRIMARIES[self.mode][i], PRIMARY_LABELS[self.mode][i])
                        for i in range(3)]
        self.counts = [0, 0, 0]  # dosi arrivate nel calderone
        self.pending = [0, 0, 0]  # dosi ancora in caduta
        self.drops: list[Drop] = []
        self.particles = ParticleSystem()
        self.current_name = EMPTY_NAME
        self.name_pop = 0.0
        self.full_msg = 0.0  # timer del fumetto "Pieno!"
        self.confirm_quit = False

        self.selector = ModeSelector(272, C.MODE_BUTTONS_Y, C.MODE_BUTTON_SIZE)
        self.empty_btn = Button(pygame.Rect(*C.EMPTY_BUTTON), C.BTN_EMPTY, icon_bucket, "Svuota", 34,
                                hit_padding=14)
        self.mute_btn = Button(pygame.Rect(*C.MUTE_BUTTON_POS, C.SMALL_BUTTON, C.SMALL_BUTTON), C.BTN_SOUND,
                               icon_sound)
        self.mute_btn.icon_args = (False,)
        self.full_btn = Button(pygame.Rect(*C.FULLSCREEN_BUTTON_POS, C.SMALL_BUTTON, C.SMALL_BUTTON),
                               C.BTN_FULLSCREEN, icon_fullscreen)
        self.yes_btn = Button(pygame.Rect(332, 430, 170, 80), C.BTN_YES, None, "Sì", 40)
        self.no_btn = Button(pygame.Rect(522, 430, 170, 80), C.BTN_NO, None, "No", 40)
        self._dim = pygame.Surface((C.LOGICAL_W, C.LOGICAL_H), pygame.SRCALPHA)
        self._dim.fill((20, 10, 40, 150))

    # ------------------------------------------------------------------ finestra
    @staticmethod
    def _initial_window_size() -> tuple[int, int]:
        """1024x768, ma ridotta (stesse proporzioni) se lo schermo è più piccolo."""
        w, h = C.LOGICAL_W, C.LOGICAL_H
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
            f = min(1.0, (dw - 60) / w, (dh - 120) / h)
            if f < 1.0:
                w, h = max(320, int(w * f)), max(240, int(h * f))
        except Exception:
            pass
        return (w, h)

    def toggle_fullscreen(self) -> None:
        try:
            if not self.fullscreen:
                self._windowed_size = self.screen.get_size()
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                self.fullscreen = True
            else:
                self.screen = pygame.display.set_mode(self._windowed_size, pygame.RESIZABLE)
                self.fullscreen = False
        except Exception as exc:  # se il cambio fallisce, si resta come prima
            print(f"[schermo] cambio modalità non riuscito: {exc}")
            self.screen = pygame.display.get_surface() or self.screen

    def _to_logical(self, pos: tuple[float, float]) -> tuple[float, float]:
        ox, oy = self._view_offset
        s = self._view_scale or 1.0
        return ((pos[0] - ox) / s, (pos[1] - oy) / s)

    def _present(self) -> None:
        """Scala la superficie logica sulla finestra mantenendo le proporzioni (bande nere)."""
        screen = pygame.display.get_surface()
        if screen is None:
            return
        ww, wh = screen.get_size()
        if ww < 2 or wh < 2:
            return
        scale = min(ww / C.LOGICAL_W, wh / C.LOGICAL_H)
        size = (max(1, int(C.LOGICAL_W * scale)), max(1, int(C.LOGICAL_H * scale)))
        self._view_scale = scale
        self._view_offset = ((ww - size[0]) // 2, (wh - size[1]) // 2)
        if size == (C.LOGICAL_W, C.LOGICAL_H):
            screen.blit(self.canvas, self._view_offset)
        else:
            screen.fill((0, 0, 0))
            screen.blit(pygame.transform.smoothscale(self.canvas, size), self._view_offset)
        pygame.display.flip()

    # ------------------------------------------------------------------ logica
    @property
    def cauldron(self) -> Cauldron:
        return self.cauldrons[self.mode]

    @property
    def theme(self) -> C.Theme:
        return C.THEMES[self.mode]

    def _doses_total(self) -> int:
        return sum(self.counts) + sum(self.pending)

    def set_mode(self, mode: Mode) -> None:
        if mode is self.mode:
            return
        self.mode = mode
        self.selector.set_mode(mode)
        self._clear_all()
        for p in self.potions:
            p.set_look(PRIMARIES[mode][p.index], PRIMARY_LABELS[mode][p.index])
        self.audio.play("click")

    def _clear_all(self) -> None:
        self.counts = [0, 0, 0]
        self.pending = [0, 0, 0]
        self.drops.clear()
        self.particles.clear()
        for c in self.cauldrons.values():
            c.reset()
        self.current_name = EMPTY_NAME
        self.name_pop = 0.0

    def add_dose(self, index: int) -> None:
        potion = self.potions[index]
        if self.cauldron.busy:  # sta versando: la pozione fa solo un saltino
            potion.bounce()
            return
        if self._doses_total() >= C.MAX_DOSES:
            # Calderone pieno: feedback gentile (fumetto + scossa), nessun errore.
            potion.shake()
            self.cauldron.shake()
            self.full_msg = 1.4
            self.audio.play("full")
            return
        self.pending[index] += 1
        potion.bounce()
        self.audio.play("drop")
        c = self.cauldron
        self.drops.append(Drop(index, potion.drop_origin, c.mouth_x + random.uniform(-22, 22), c.rim_world_y,
                               PRIMARIES[self.mode][index], c.surface_world_y))

    def _on_land(self, drop: Drop) -> None:
        i = drop.index
        self.pending[i] -= 1
        self.counts[i] += 1
        rgb = mix(self.mode, self.counts)
        self.cauldron.set_state(rgb, sum(self.counts))
        self.cauldron.splash()
        self.particles.splash(drop.x, self.cauldron.surface_world_y(), drop.color)
        self.audio.play(f"plop{i}")
        name = color_name(self.mode, rgb)
        if name != self.current_name:
            self.current_name = name
            self.name_pop = 1.0
            if kinds(self.counts) >= 2:  # nuovo colore "secondario": festa!
                self.particles.sparkles(self.cauldron.center[0], self.cauldron.surface_world_y() - 10)
                self.audio.play("jingle")

    def empty_cauldron(self) -> None:
        self.empty_btn.press()
        if self._doses_total() == 0 or self.cauldron.busy:
            return
        self.drops.clear()
        self.counts = [0, 0, 0]
        self.pending = [0, 0, 0]
        if self.cauldron.pour():
            self.audio.play("glug")
        self.current_name = EMPTY_NAME
        self.name_pop = 1.0

    def toggle_mute(self) -> None:
        muted = self.audio.toggle_mute()
        self.mute_btn.icon_args = (muted,)
        self.mute_btn.dimmed = muted
        if not muted:
            self.audio.play("click")

    # ------------------------------------------------------------------ eventi
    def handle_event(self, e: pygame.event.Event) -> None:
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_F11, pygame.K_f):
                self.toggle_fullscreen()
            elif e.key == pygame.K_m:
                self.toggle_mute()
            elif e.key == pygame.K_ESCAPE:
                # ESC non chiude mai il gioco di colpo: esce dal pieno schermo o chiede conferma.
                if self.confirm_quit:
                    self.confirm_quit = False
                elif self.fullscreen:
                    self.toggle_fullscreen()
                else:
                    self.confirm_quit = True
            elif e.key == pygame.K_RETURN and self.confirm_quit:
                self.running = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._click(self._to_logical(e.pos))

    def _click(self, pos: tuple[float, float]) -> None:
        if self.confirm_quit:
            if self.yes_btn.hit(pos):
                self.running = False
            elif self.no_btn.hit(pos):
                self.confirm_quit = False
            return
        mode = self.selector.hit(pos)
        if mode is not None:
            self.selector.buttons[mode].press()
            self.set_mode(mode)
        elif self.mute_btn.hit(pos):
            self.mute_btn.press()
            self.toggle_mute()
        elif self.full_btn.hit(pos):
            self.full_btn.press()
            self.toggle_fullscreen()
        elif self.empty_btn.hit(pos):
            self.empty_cauldron()
        else:
            for p in self.potions:
                if p.hit(pos, C.HIT_PADDING):
                    self.add_dose(p.index)
                    break

    # ------------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        self.t += dt
        mouse = self._to_logical(pygame.mouse.get_pos())
        for p in self.potions:
            p.update(dt, p.hit(mouse, C.HIT_PADDING) and not self.confirm_quit)
        self.selector.update(dt, mouse)
        for b in (self.empty_btn, self.mute_btn, self.full_btn, self.yes_btn, self.no_btn):
            b.update(dt, mouse)

        landed = [d for d in self.drops if d.update(dt)]
        for d in landed:
            self.drops.remove(d)
            self._on_land(d)

        self.cauldron.update(dt)
        spout = self.cauldron.spout_world()
        if spout:  # il liquido esce dal bordo mentre il calderone è inclinato
            for _ in range(2):
                self.particles.pour_drop(spout[0], spout[1], self.cauldron.liquid_rgb)
        self.particles.update(dt)
        self.name_pop = max(0.0, self.name_pop - dt * 2.5)
        self.full_msg = max(0.0, self.full_msg - dt)

    # ------------------------------------------------------------------ disegno
    def draw(self) -> None:
        s = self.canvas
        th = self.theme
        s.blit(self.backgrounds[self.mode], (0, 0))
        self._draw_decor(s)
        self.cauldron.draw_glow(s)

        for p in self.potions:
            draw_dose_counter(s, p.center[0], 96, self.counts[p.index] + self.pending[p.index],
                              PRIMARIES[self.mode][p.index], th.panel_border if self.mode is Mode.PAINT else (170, 160, 230))
        for p in self.potions:
            p.draw(s, self.t)
        self.cauldron.draw(s, self.t)

        self._draw_name_panel(s)
        self.selector.draw(s, th.shadow)
        self.empty_btn.draw(s, th.shadow)
        self.mute_btn.draw(s, th.shadow)
        self.full_btn.draw(s, th.shadow)
        if self.mode is Mode.LIGHT:
            self._draw_light_badge(s)

        for d in self.drops:
            d.draw(s)
        self.particles.draw(s)
        if self.full_msg > 0:
            self._draw_full_bubble(s)
        if self.confirm_quit:
            self._draw_dialog(s)

    def _draw_decor(self, s: pygame.Surface) -> None:
        if self.mode is Mode.LIGHT:
            for x, y, ph, size in self.stars:
                v = 150 + int(105 * (0.5 + 0.5 * math.sin(self.t * 2 + ph)))
                pygame.draw.circle(s, (v, v, min(255, v + 20)), (x, y), size)
        else:
            for x, y, r in self.clouds:
                pygame.draw.circle(s, (255, 255, 255), (x, y), r)
                pygame.draw.circle(s, (255, 255, 255), (x + r * 0.9, y + r * 0.2), r * 0.7)
                pygame.draw.circle(s, (255, 255, 255), (x - r * 0.9, y + r * 0.25), r * 0.6)

    def _draw_name_panel(self, s: pygame.Surface) -> None:
        th = self.theme
        rect = pygame.Rect(C.NAME_PANEL)
        draw_rounded(s, rect.move(0, 6), th.shadow, 36)
        draw_rounded(s, rect, th.panel, 36, border=5, border_color=th.panel_border)
        empty = self.current_name == EMPTY_NAME
        if not empty:  # campione di colore a sinistra
            c = self.cauldron.liquid_rgb
            pygame.draw.circle(s, th.panel_border, (rect.x + 62, rect.centery), 36)
            pygame.draw.circle(s, c, (rect.x + 62, rect.centery), 31)
            pygame.draw.circle(s, (255, 255, 255), (rect.x + 52, rect.centery - 10), 6)
        txt = text_surface(self.current_name, 40 if empty else 60, th.text)
        if self.name_pop > 0:  # piccolo "pop" quando il nome cambia
            f = 1 + 0.22 * math.sin(self.name_pop * math.pi)
            txt = pygame.transform.smoothscale(txt, (int(txt.get_width() * f), int(txt.get_height() * f)))
        cx = rect.centerx + (0 if empty else 40)
        s.blit(txt, txt.get_rect(center=(cx, rect.centery + 2)))

    def _draw_light_badge(self, s: pygame.Surface) -> None:
        th = self.theme
        rect = pygame.Rect(16, 470, 280, 100)
        draw_rounded(s, rect.move(0, 5), th.shadow, 28)
        draw_rounded(s, rect, th.panel, 28, border=4, border_color=(255, 230, 90))
        icon_bulb(s, rect.x + 48, rect.centery, 70)
        for i, line in enumerate(("Magia della", "luce!")):
            t = text_surface(line, 27, (255, 236, 120))
            s.blit(t, (rect.x + 92, rect.centery - 31 + i * 34))

    def _draw_full_bubble(self, s: pygame.Surface) -> None:
        pop = smoothstep((1.4 - self.full_msg) / 0.15) * (1 if self.full_msg > 0.25 else self.full_msg / 0.25)
        txt = text_surface("Pieno!", 44, self.theme.text)
        w, h = int(txt.get_width() + 56), 64
        rect = pygame.Rect(0, 0, int(w * pop), int(h * pop))
        rect.center = (C.CAULDRON_CENTER[0], 398)
        if rect.width < 10:
            return
        draw_rounded(s, rect.move(0, 5), self.theme.shadow, 30)
        draw_rounded(s, rect, self.theme.panel, 30, border=4, border_color=self.theme.panel_border)
        if pop > 0.9:
            s.blit(txt, txt.get_rect(center=rect.center))

    def _draw_dialog(self, s: pygame.Surface) -> None:
        s.blit(self._dim, (0, 0))
        rect = pygame.Rect(0, 0, 520, 290)
        rect.center = (C.LOGICAL_W // 2, 400)
        draw_rounded(s, rect.move(0, 8), (30, 20, 60), 40)
        draw_rounded(s, rect, (255, 255, 255), 40, border=6, border_color=(120, 90, 170))
        txt = text_surface("Vuoi uscire?", 58, (64, 40, 96))
        s.blit(txt, txt.get_rect(center=(rect.centerx, rect.y + 90)))
        self.yes_btn.draw(s, (40, 30, 70))
        self.no_btn.draw(s, (40, 30, 70))

    # ------------------------------------------------------------------ ciclo
    def step(self, dt: float) -> None:
        """Un fotogramma: eventi, aggiornamento, disegno."""
        for e in pygame.event.get():
            self.handle_event(e)
        self.update(dt)
        self.draw()
        self._present()

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while self.running:
            dt = min(0.05, self.clock.tick(C.FPS) / 1000.0)
            self.step(dt)
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()
