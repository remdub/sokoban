# src/menu.py — All menu screens: main, level select, pause, win, options

from __future__ import annotations
import math
from typing import List, Optional, Callable
import pygame
import settings
import src.savegame as savegame
import src.student as student
import src.audio as audio

_CHALK_BG   = (28,  68,  40)   # chalkboard green
_CHALK_LINE = (38,  88,  52)   # faint ruled lines
_CHALK_TEXT = (185, 210, 188)  # off-white chalk
_CHALK_DUST = (155, 178, 158)  # dimmer dust particles

# ── Mini sokoban background animation ─────────────────────────────────────────
_LEFT_GRID  = ["####", "#. #", "#  #", "#  #", "#  #", "####"]
_RIGHT_GRID = ["####", "#  #", "#  #", "# .#", "####"]
_MINI_STEP_FRAMES  = 50   # frames between moves
_MINI_PAUSE_FRAMES = 80   # pause frames after solving before reset


def _mini_positions(player_start, box_start, moves):
    """Return list of (player, box) for each step; index 0 = initial state."""
    positions = [(player_start, box_start)]
    p, b = player_start, box_start
    for dx, dy in moves:
        np = (p[0] + dx, p[1] + dy)
        if np == b:
            b = (b[0] + dx, b[1] + dy)
        p = np
        positions.append((p, b))
    return positions


def _draw_mini_board(surf, scale, tick, ox, oy, grid, player_start, box_start, moves):
    """Draw an animated mini sokoban board at logical offset (ox, oy)."""
    ts     = settings.TILE_SIZE
    cycle  = len(moves) * _MINI_STEP_FRAMES + _MINI_PAUSE_FRAMES
    step   = min(len(moves), (tick % cycle) // _MINI_STEP_FRAMES)
    pos    = _mini_positions(player_start, box_start, moves)
    player, box = pos[step]

    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            rx = (ox + c * ts) * scale
            ry = (oy + r * ts) * scale
            sw = ts * scale
            if ch == '#':
                pygame.draw.rect(surf, settings.COLOR_WALL,  (rx, ry, sw, sw))
                pygame.draw.line(surf, settings.WHITE,       (rx, ry),      (rx+sw-1, ry))
                pygame.draw.line(surf, settings.WHITE,       (rx, ry),      (rx, ry+sw-1))
                pygame.draw.line(surf, settings.DARK_GRAY,  (rx, ry+sw-1), (rx+sw-1, ry+sw-1))
                pygame.draw.line(surf, settings.DARK_GRAY,  (rx+sw-1, ry), (rx+sw-1, ry+sw-1))
            elif ch in (' ', '.'):
                pygame.draw.rect(surf, settings.COLOR_FLOOR, (rx, ry, sw, sw))
                if ch == '.':
                    m = 3 * scale
                    pygame.draw.rect(surf, settings.COLOR_TARGET,
                                     (rx+m, ry+sw//2-scale, sw-2*m, 2*scale))
                    pygame.draw.rect(surf, settings.COLOR_TARGET,
                                     (rx+sw//2-scale, ry+m, 2*scale, sw-2*m))

    # Box
    bc, br = box
    rx = (ox + bc * ts) * scale
    ry = (oy + br * ts) * scale
    sw = ts * scale
    on_target = grid[br][bc] == '.'
    color = settings.COLOR_BOX_DONE if on_target else settings.COLOR_BOX
    pygame.draw.rect(surf, color, (rx, ry, sw, sw))
    pygame.draw.line(surf, settings.WHITE, (rx, ry),      (rx+sw-1, ry))
    pygame.draw.line(surf, settings.WHITE, (rx, ry),      (rx, ry+sw-1))
    pygame.draw.line(surf, settings.BLACK, (rx, ry+sw-1), (rx+sw-1, ry+sw-1))
    pygame.draw.line(surf, settings.BLACK, (rx+sw-1, ry), (rx+sw-1, ry+sw-1))

    # Player
    pc, pr = player
    rx = (ox + pc * ts) * scale
    ry = (oy + pr * ts) * scale
    pygame.draw.rect(surf, settings.COLOR_PLAYER,
                     (rx+3*scale, ry+4*scale, (ts-6)*scale, (ts-5)*scale))  # body
    pygame.draw.rect(surf, settings.COLOR_PLAYER,
                     (rx+4*scale, ry+1*scale, (ts-8)*scale, 4*scale))        # head
    pygame.draw.rect(surf, settings.BLACK,
                     (rx+5*scale, ry+2*scale, 2*scale, 2*scale))              # eye

    cols = len(grid[0])
    rows = len(grid)
    return pygame.Rect(ox * scale, oy * scale, cols * ts * scale, rows * ts * scale)


# ── Shared helpers ─────────────────────────────────────────────────────────────
# All x, y coordinates are in logical (320×240) units.
# They are multiplied by `scale` just before blitting onto the window surface.

def _draw_text(surf, font, text, color, x, y, scale=1):
    s = font.render(text, False, color)
    surf.blit(s, (x * scale, y * scale))

def _draw_centered(surf, font, text, color, cx, y, scale=1):
    s = font.render(text, False, color)
    surf.blit(s, (cx * scale - s.get_width() // 2, y * scale))

def _draw_stars(surf, font, n: int, cx: int, y: int, scale=1) -> None:
    star_str = "*" * n + "." * (3 - n)
    color = settings.COLOR_STAR if n > 0 else settings.COLOR_STAR_EMPTY
    _draw_centered(surf, font, star_str, color, cx, y, scale)


def _draw_trophy_bg(surf, font, tick, scale):
    lw, lh = settings.LOGICAL_W, settings.LOGICAL_H
    # Background
    surf.fill((10, 10, 40))
    # Gold border
    pygame.draw.rect(surf, (200, 160, 0),
                     (0, 0, lw * scale, lh * scale), 4 * scale)
    pygame.draw.rect(surf, (240, 200, 40),
                     (3 * scale, 3 * scale, (lw - 6) * scale, (lh - 6) * scale),
                     scale)
    # Scattered stars — kept in left/right margins and top strip
    star_positions = [
        (20, 20), (55, 12), (270, 18), (298, 25),
        (10, 90), (68, 105), (250, 80), (305, 100),
        (15, 170), (62, 185), (255, 165), (300, 180),
    ]
    for i, (sx, sy) in enumerate(star_positions):
        dy = int(2 * math.sin(tick * 0.04 + i * 0.9))
        _draw_centered(surf, font, "*", (220, 180, 0), sx, sy + dy, scale)

    # ── Trophy cup — right zone (centred at x=278) ───────────────────────────
    tx = 278
    gold = (220, 170, 20)
    dark = (10, 10, 40)
    bowl = [
        (tx - 22, 140), (tx + 22, 140),
        (tx + 14, 163), (tx +  8, 167),
        (tx -  8, 167), (tx - 14, 163),
    ]
    pygame.draw.polygon(surf, gold,
                        [(x * scale, y * scale) for x, y in bowl])
    inner = [(tx - 14, 143), (tx + 14, 143), (tx + 9, 161), (tx - 9, 161)]
    pygame.draw.polygon(surf, (240, 210, 60),
                        [(x * scale, y * scale) for x, y in inner])
    # Left handle
    pygame.draw.ellipse(surf, gold,
                        ((tx - 26) * scale, 148 * scale, 10 * scale, 12 * scale))
    pygame.draw.ellipse(surf, dark,
                        ((tx - 24) * scale, 150 * scale,  6 * scale,  8 * scale))
    # Right handle
    pygame.draw.ellipse(surf, gold,
                        ((tx + 16) * scale, 148 * scale, 10 * scale, 12 * scale))
    pygame.draw.ellipse(surf, dark,
                        ((tx + 18) * scale, 150 * scale,  6 * scale,  8 * scale))
    # Stem
    pygame.draw.rect(surf, gold,
                     ((tx - 4) * scale, 167 * scale, 8 * scale, 10 * scale))
    # Base plates
    pygame.draw.rect(surf, gold,
                     ((tx - 18) * scale, 177 * scale, 36 * scale, 5 * scale))
    pygame.draw.rect(surf, gold,
                     ((tx - 14) * scale, 182 * scale, 28 * scale, 4 * scale))

    # ── Victory podium — left zone (centred at x=42) ─────────────────────────
    BASE_Y = 215
    podium = [
        # (label, colour, x_start, height, label_cx)
        ("2", (180, 180, 200), 19, 25, 26),
        ("1", (220, 170,  20), 35, 35, 42),
        ("3", (160, 100,  40), 51, 18, 58),
    ]
    for label, colour, px, ph, lcx in podium:
        top_y = BASE_Y - ph
        pygame.draw.rect(surf, colour,
                         (px * scale, top_y * scale, 14 * scale, ph * scale))
        pygame.draw.rect(surf, (10, 10, 40),
                         (px * scale, top_y * scale, 14 * scale, ph * scale), scale)
        _draw_centered(surf, font, label, (240, 240, 240), lcx, top_y + 2, scale)


def _draw_chalkboard_bg(surf, font, tick, scale):
    lw, lh = settings.LOGICAL_W, settings.LOGICAL_H

    # Chalkboard fill
    surf.fill(_CHALK_BG)

    # Horizontal ruled lines every 12 logical px
    for y in range(0, lh, 12):
        pygame.draw.line(surf, _CHALK_LINE,
                         (0, y * scale), (lw * scale - 1, y * scale))

    # Wooden frame border
    pygame.draw.rect(surf, settings.BROWN,
                     (0, 0, lw * scale, lh * scale), 6 * scale)
    pygame.draw.rect(surf, settings.DARK_GRAY,
                     (2 * scale, 2 * scale, (lw - 4) * scale, (lh - 4) * scale),
                     scale)

    # Animated chalk dust (10 particles, drift upward with tick)
    for i in range(10):
        px = (i * 31 + 6) % lw
        py = lh - 25 - (tick // 3 + i * 23) % (lh - 30)
        if 0 <= py < lh:
            pygame.draw.rect(surf, _CHALK_DUST,
                             (px * scale, py * scale, scale, scale))


# ── Main Menu ─────────────────────────────────────────────────────────────────

class MainMenu:
    ITEMS = [
        ("ENTRAÎNEMENT",   "play"),
        ("TOURNOI",        "tournoi"),
        ("QUITTER",        "quit"),
    ]

    def __init__(self):
        self._selected = 0
        self._tick = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Returns an action string or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(self.ITEMS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(self.ITEMS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_CONFIRM:
            return self.ITEMS[self._selected][1]
        elif event.key in settings.KEY_PAUSE:
            return 'profile_select'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1, student_name: str = "") -> None:
        self._tick += 1
        _draw_chalkboard_bg(surf, font, self._tick, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        # Title
        _draw_centered(surf, font, "SOKOBAN", settings.COLOR_MENU_TITLE, cx, 30, scale)

        # Subtitle
        _draw_centered(surf, font, "INSTITUTS SAINT-LUC MONS", settings.DARK_GRAY, cx, 48, scale)

        # Active student name
        if student_name:
            _draw_centered(surf, font, f"* {student_name.upper()} *",
                           settings.CYAN, cx, 64, scale)

        # Menu items
        item_y_start = 90
        for i, (label, _) in enumerate(self.ITEMS):
            color = (settings.COLOR_MENU_SELECT if i == self._selected
                     else settings.COLOR_MENU_ITEM)
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + label, color, cx,
                           item_y_start + i * 20, scale)

        # Pulsing cursor
        if (self._tick // 30) % 2 == 0:
            sel_y = item_y_start + self._selected * 20
            _draw_centered(surf, font, "_", settings.COLOR_HIGHLIGHT, cx,
                           sel_y + 10, scale)

        # Footer
        _draw_centered(surf, font, "FLÈCHES / ZQSD  ENTRÉE    ÉCHAP : Sélection joueur",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Entrainement Sub-Menu ─────────────────────────────────────────────────────

class EntrainementMenu:
    ITEMS = [
        ("CHOISIR NIVEAU", "level_select"),
        ("RETOUR",         "back"),
    ]

    def __init__(self):
        self._selected = 0
        self._tick = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(self.ITEMS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(self.ITEMS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_CONFIRM:
            return self.ITEMS[self._selected][1]
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1, student_name: str = "") -> None:
        self._tick += 1
        _draw_chalkboard_bg(surf, font, self._tick, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "ENTRAÎNEMENT", settings.COLOR_MENU_TITLE, cx, 30, scale)

        if student_name:
            _draw_centered(surf, font, f"* {student_name.upper()} *",
                           settings.CYAN, cx, 48, scale)

        item_y_start = 90
        for i, (label, _) in enumerate(self.ITEMS):
            color = (settings.COLOR_MENU_SELECT if i == self._selected
                     else settings.COLOR_MENU_ITEM)
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + label, color, cx,
                           item_y_start + i * 20, scale)

        if (self._tick // 30) % 2 == 0:
            sel_y = item_y_start + self._selected * 20
            _draw_centered(surf, font, "_", settings.COLOR_HIGHLIGHT, cx,
                           sel_y + 10, scale)

        _draw_centered(surf, font, "FLÈCHES / ZQSD  ENTRÉE  ÉCHAP",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Level Select ──────────────────────────────────────────────────────────────

GRID_COLS = 5
GRID_ROWS = 4
PAGE_SIZE = GRID_COLS * GRID_ROWS   # 20 per page


class LevelSelect:
    def __init__(self, pack_names: List[str]):
        self.pack_names   = pack_names
        self.pack_idx     = 0
        self._cursor      = 0
        self._page        = 0
        self._level_count = [0] * len(pack_names)
        self.student_name: str = ""

    def set_pack_sizes(self, sizes: List[int]) -> None:
        self._level_count = sizes

    def set_pack(self, pack_idx: int) -> None:
        self.pack_idx = pack_idx % len(self.pack_names)
        self._cursor = 0
        self._page   = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        if event.type != pygame.KEYDOWN:
            return None

        unlocked = student.get_unlocked(self.student_name, self.pack_names[self.pack_idx])
        total    = self._level_count[self.pack_idx]

        if event.key in settings.KEY_LEFT:
            if self._cursor % GRID_COLS > 0:
                self._cursor -= 1
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_RIGHT:
            if (self._cursor % GRID_COLS < GRID_COLS - 1
                    and self._cursor + 1 < total):
                self._cursor += 1
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_UP:
            if self._cursor >= GRID_COLS:
                self._cursor -= GRID_COLS
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_DOWN:
            if self._cursor + GRID_COLS < total:
                self._cursor += GRID_COLS
            audio.play_sfx('move.wav')
        elif event.key == pygame.K_PAGEUP or event.key in settings.KEY_PREV:
            # previous pack
            self.pack_idx = (self.pack_idx - 1) % len(self.pack_names)
            self._cursor = 0
        elif event.key == pygame.K_PAGEDOWN or event.key in settings.KEY_NEXT:
            # next pack
            self.pack_idx = (self.pack_idx + 1) % len(self.pack_names)
            self._cursor = 0
        elif event.key in settings.KEY_CONFIRM:
            level_idx = self._page * PAGE_SIZE + self._cursor
            if level_idx < unlocked:
                return {'pack': self.pack_idx, 'level': level_idx}
        elif event.key in settings.KEY_PAUSE:
            return {'action': 'back'}
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             font_lg: pygame.font.Font, scale: int = 1) -> None:
        surf.fill(settings.COLOR_MENU_BG)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        pack_name = self.pack_names[self.pack_idx]
        _draw_centered(surf, font_lg,
                       f"< {pack_name} >", settings.COLOR_MENU_TITLE, cx, 8, scale)

        unlocked = student.get_unlocked(self.student_name, pack_name)
        total    = self._level_count[self.pack_idx]

        cell_w = 50
        cell_h = 30
        grid_w = GRID_COLS * cell_w
        gx0    = (lw - grid_w) // 2
        gy0    = 28

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                idx = self._page * PAGE_SIZE + row * GRID_COLS + col
                if idx >= total:
                    break
                rx = gx0 + col * cell_w
                ry = gy0 + row * cell_h
                is_sel = (idx == self._page * PAGE_SIZE + self._cursor)
                is_locked = idx >= unlocked

                # Cell background (scaled)
                bg = (settings.DARK_BLUE if is_sel else settings.BLACK)
                pygame.draw.rect(surf, bg,
                    ((rx + 1) * scale, (ry + 1) * scale,
                     (cell_w - 2) * scale, (cell_h - 2) * scale))
                border = (settings.COLOR_HIGHLIGHT if is_sel
                          else (settings.DARK_GRAY if is_locked else settings.LIGHT_GRAY))
                pygame.draw.rect(surf, border,
                    ((rx + 1) * scale, (ry + 1) * scale,
                     (cell_w - 2) * scale, (cell_h - 2) * scale), scale)

                # Level number
                num_color = (settings.DARK_GRAY if is_locked else settings.WHITE)
                _draw_centered(surf, font, f"{idx + 1:02d}", num_color,
                               rx + cell_w // 2, ry + 4, scale)

                # Stars
                sc = student.get_score(self.student_name, pack_name, idx)
                stars = sc.get('stars', 0) if sc else 0
                if not is_locked and stars > 0:
                    _draw_stars(surf, font, stars, rx + cell_w // 2, ry + 16, scale)
                elif is_locked:
                    _draw_centered(surf, font, "VERROU", settings.DARK_GRAY,
                                   rx + cell_w // 2, ry + 16, scale)

        _draw_centered(surf, font_lg, "ÉCHAP : retour    PgHaut / PgBas : changer de pack",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Tournoi Pack Select ───────────────────────────────────────────────────────

class TournoiPackSelectScreen:
    def __init__(self):
        self._selected = 0
        self._tick     = 0

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(settings.LEVEL_PACKS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(settings.LEVEL_PACKS)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_CONFIRM:
            return {'pack': self._selected}
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        self._tick += 1
        _draw_chalkboard_bg(surf, font, self._tick, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "TOURNOI", settings.COLOR_MENU_TITLE, cx, 25, scale)
        _draw_centered(surf, font, "CHOISIR UN PACK", settings.CYAN, cx, 42, scale)

        for i, pack in enumerate(settings.LEVEL_PACKS):
            color  = (settings.COLOR_MENU_SELECT if i == self._selected
                      else settings.COLOR_MENU_ITEM)
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + pack['name'].upper(),
                           color, cx, 80 + i * 22, scale)

        _draw_centered(surf, font, "FLÈCHES  ENTRÉE:JOUER  ÉCHAP:RETOUR",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Pause Screen ──────────────────────────────────────────────────────────────

class PauseScreen:
    _NORMAL_ITEMS = [
        ("REPRENDRE",      "resume"),
        ("RECOMMENCER",    "restart"),
        ("CHOISIR NIVEAU", "level_select"),
        ("MENU PRINCIPAL", "main_menu"),
    ]
    _TOURNOI_ITEMS = [
        ("REPRENDRE",      "resume"),
        ("RECOMMENCER",    "restart"),
        ("MENU PRINCIPAL", "main_menu"),
    ]

    @property
    def _items(self):
        return self._TOURNOI_ITEMS if self.tournoi_mode else self._NORMAL_ITEMS

    def __init__(self):
        self._selected     = 0
        self.tournoi_mode  = False
        self._confirm_quit = False
        self._confirm_sel  = 1   # 0 = OUI, 1 = NON (default: NON to avoid accidental quit)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None

        # ── Confirmation sub-menu ────────────────────────────────────────────
        if self._confirm_quit:
            if event.key in settings.KEY_UP or event.key in settings.KEY_DOWN:
                self._confirm_sel = 1 - self._confirm_sel   # toggle OUI / NON
            elif event.key in settings.KEY_CONFIRM:
                self._confirm_quit = False
                if self._confirm_sel == 0:   # OUI
                    return 'main_menu'
                # NON — fall back to pause menu (no action)
            elif event.key in settings.KEY_PAUSE:
                self._confirm_quit = False   # ESC cancels
            return None

        # ── Normal pause menu ────────────────────────────────────────────────
        if event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(self._items)
        elif event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(self._items)
        elif event.key in settings.KEY_CONFIRM:
            action = self._items[self._selected][1]
            if action == 'main_menu' and self.tournoi_mode:
                self._confirm_quit = True
                self._confirm_sel  = 1   # reset to NON each time
                return None
            return action
        elif event.key in settings.KEY_PAUSE:
            return 'resume'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        # Darken background
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        lw = settings.LOGICAL_W
        cx = lw // 2
        _draw_centered(surf, font, "PAUSE", settings.COLOR_MENU_TITLE, cx, 60, scale)
        _draw_centered(surf, font, "ZQSD/FLÈCHES  U:annuler  R:refaire  F5:restart",
                       settings.DARK_GRAY, cx, 82, scale)

        for i, (label, _) in enumerate(self._items):
            color = (settings.COLOR_MENU_SELECT if i == self._selected
                     else settings.COLOR_MENU_ITEM)
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + label, color, cx, 100 + i * 18, scale)

        if self._confirm_quit:
            overlay2 = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            overlay2.fill((0, 0, 0, 120))
            surf.blit(overlay2, (0, 0))

            _draw_centered(surf, font, "Quitter le tournoi ?",
                           (240, 80, 80), cx, 130, scale)
            for i, label in enumerate(("OUI", "NON")):
                color = (settings.COLOR_MENU_SELECT if i == self._confirm_sel
                         else settings.COLOR_MENU_ITEM)
                prefix = "> " if i == self._confirm_sel else "  "
                _draw_centered(surf, font, prefix + label, color, cx, 150 + i * 18, scale)


# ── Win Screen ────────────────────────────────────────────────────────────────

class WinScreen:
    _NORMAL_ITEMS = [
        ("NIVEAU SUIVANT", "next_level"),
        ("RÉESSAYER",      "retry"),
        ("CHOISIR NIVEAU", "level_select"),
    ]
    _TOURNOI_ITEMS = [
        ("CONTINUER",  "next_level"),
        ("RÉESSAYER",  "retry"),
    ]

    def __init__(self):
        self._selected     = 0
        self._tick         = 0
        self._tournoi_score: Optional[int] = None

    @property
    def _items(self):
        return (self._TOURNOI_ITEMS if self._tournoi_score is not None
                else self._NORMAL_ITEMS)

    def reset(self, tournoi_score: Optional[int] = None):
        self._selected     = 0
        self._tick         = 0
        self._tournoi_score = tournoi_score

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        items = self._items
        if event.key in settings.KEY_LEFT or event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(items)
        elif event.key in settings.KEY_RIGHT or event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(items)
        elif event.key in settings.KEY_CONFIRM:
            return items[self._selected][1]
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             level_name: str, moves: int, pushes: int,
             elapsed: float, stars: int, is_best: bool,
             scale: int = 1, tournoi_score: Optional[int] = None) -> None:
        self._tick += 1

        # Win banner overlay
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 80, 200))
        surf.blit(overlay, (0, 0))

        lw = settings.LOGICAL_W
        cx = lw // 2

        _draw_centered(surf, font, "NIVEAU RÉUSSI !", settings.COLOR_WIN_BG, cx + 1, 41, scale)
        _draw_centered(surf, font, "NIVEAU RÉUSSI !", settings.YELLOW, cx, 40, scale)

        if tournoi_score is not None:
            # Tournoi mode: show score instead of stars
            _draw_centered(surf, font, f"SCORE : {tournoi_score:4d}",
                           settings.CYAN, cx, 65, scale)
        else:
            # Stars with animation
            star_y = 60
            for i in range(3):
                offset = int(3 * math.sin(self._tick * 0.1 + i * 1.2))
                c = settings.COLOR_STAR if i < stars else settings.COLOR_STAR_EMPTY
                star_x = cx - 16 + i * 16
                _draw_centered(surf, font, "*", c, star_x, star_y + offset, scale)

        # Stats
        mins = int(elapsed) // 60
        secs = int(elapsed) % 60
        _draw_centered(surf, font, f"MOUVEMENTS: {moves:4d}", settings.WHITE, cx, 82, scale)
        _draw_centered(surf, font, f"POUSSÉES  : {pushes:4d}", settings.WHITE, cx, 94, scale)
        _draw_centered(surf, font, f"TEMPS     : {mins:02d}:{secs:02d}", settings.WHITE, cx, 106, scale)

        if is_best and tournoi_score is None:
            _draw_centered(surf, font, "NOUVEAU RECORD !", settings.CYAN, cx, 120, scale)

        # Action buttons
        items = self._items
        for i, (label, _) in enumerate(items):
            color = (settings.COLOR_MENU_SELECT if i == self._selected
                     else settings.DARK_GRAY)
            _draw_centered(surf, font, label, color, cx, 148 + i * 14, scale)


# ── Options Screen ────────────────────────────────────────────────────────────

class OptionsScreen:
    def __init__(self):
        self._selected = 0

    @property
    def _items(self):
        sfx_pct   = int(audio.get_sfx_volume()   * 100)
        mus_pct   = int(audio.get_music_volume()  * 100)
        crt_str   = "OUI" if savegame.get('crt_enabled', True) else "NON"
        full_str  = "OUI" if savegame.get('fullscreen', False)  else "NON"
        return [
            f"SON SFX     : {sfx_pct:3d}%",
            f"MUSIQUE     : {mus_pct:3d}%",
            f"EFFET CRT   : {crt_str}",
            f"PLEIN ÉCRAN : {full_str}",
            "RETOUR",
        ]

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        items = self._items

        if event.key in settings.KEY_UP:
            self._selected = (self._selected - 1) % len(items)
        elif event.key in settings.KEY_DOWN:
            self._selected = (self._selected + 1) % len(items)
        elif event.key in settings.KEY_LEFT:
            self._adjust(-1)
        elif event.key in settings.KEY_RIGHT:
            self._adjust(+1)
        elif event.key in settings.KEY_CONFIRM:
            if self._selected == len(items) - 1:
                return 'back'
            self._adjust(+1)
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def _adjust(self, delta: int) -> None:
        idx = self._selected
        if idx == 0:
            vol = round(audio.get_sfx_volume() + delta * 0.1, 1)
            audio.set_sfx_volume(vol)
            savegame.set('sfx_volume', audio.get_sfx_volume())
        elif idx == 1:
            vol = round(audio.get_music_volume() + delta * 0.1, 1)
            audio.set_music_volume(vol)
            savegame.set('music_volume', audio.get_music_volume())
        elif idx == 2:
            savegame.set('crt_enabled', not savegame.get('crt_enabled', True))
        elif idx == 3:
            savegame.set('fullscreen', not savegame.get('fullscreen', False))

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        surf.fill(settings.COLOR_MENU_BG)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2
        _draw_centered(surf, font, "OPTIONS", settings.COLOR_MENU_TITLE, cx, 20, scale)

        for i, item in enumerate(self._items):
            color = (settings.COLOR_MENU_SELECT if i == self._selected
                     else settings.COLOR_MENU_ITEM)
            _draw_centered(surf, font, item, color, cx, 50 + i * 20, scale)

        _draw_centered(surf, font, "GAUCHE/DROITE POUR MODIFIER",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Profile Select Screen ─────────────────────────────────────────────────────

class ProfileSelectScreen:
    def __init__(self):
        self._name: str       = ""
        self._students: List[str] = []
        self._student_idx: int = -1
        self._tick: int        = 0
        self._confirming: bool = False

    def refresh(self) -> None:
        import src.student as student
        self._students     = sorted(student.list_students())
        self._student_idx  = -1
        self._name         = ""
        self._confirming   = False

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        """Returns {'action':'student','name':...}, {'action':'teacher'}, {'action':'quit'}, or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if self._confirming:
            if event.key == pygame.K_o:
                return {'action': 'quit'}
            if event.key in (pygame.K_n, pygame.K_ESCAPE):
                self._confirming = False
            return None
        if event.key == pygame.K_ESCAPE:
            self._confirming = True
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            name = self._name.strip()
            if name:
                return {'action': 'student', 'name': name.lower()}
        elif event.key == pygame.K_TAB:
            return {'action': 'teacher'}
        elif event.key == pygame.K_BACKSPACE:
            if self._name:
                self._name        = self._name[:-1]
                self._student_idx = -1
        elif event.key == pygame.K_UP:
            if self._students:
                if self._student_idx < 0:
                    self._student_idx = len(self._students) - 1
                else:
                    self._student_idx = max(0, self._student_idx - 1)
                self._name = self._students[self._student_idx]
        elif event.key == pygame.K_DOWN:
            if self._students:
                if self._student_idx < 0:
                    self._student_idx = 0
                else:
                    self._student_idx = min(
                        len(self._students) - 1, self._student_idx + 1)
                self._name = self._students[self._student_idx]
        elif (event.unicode
              and event.unicode.isprintable()
              and event.unicode not in ('\t', '\r', '\n')
              and len(self._name) < 20):
            self._name        += event.unicode
            self._student_idx  = -1
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        self._tick += 1
        _draw_chalkboard_bg(surf, font, self._tick, scale)

        # Animated mini sokoban boards in the left/right margins
        rect_l = _draw_mini_board(surf, scale, self._tick,
                                  ox=10, oy=80, grid=_LEFT_GRID,
                                  player_start=(1, 4), box_start=(1, 3),
                                  moves=[(0, -1), (0, -1)])
        rect_r = _draw_mini_board(surf, scale, self._tick,
                                  ox=246, oy=82, grid=_RIGHT_GRID,
                                  player_start=(1, 2), box_start=(2, 2),
                                  moves=[(0, -1), (1, 0), (0, 1)])
        self.board_rects = [rect_l, rect_r]

        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        font_title = pygame.font.Font(None, 36)
        _draw_centered(surf, font_title, "SOKOBAN",
                       settings.COLOR_MENU_TITLE, cx, 12, scale)
        _draw_centered(surf, font, "QUI ES-TU ?",
                       settings.COLOR_MENU_TITLE, cx, 38, scale)
        _draw_centered(surf, font, "ECRIS TON NOM",
                       settings.DARK_GRAY, cx, 50, scale)
        _draw_centered(surf, font, "OU CHOISIS LE CI-DESSOUS AVEC LES FLECHES DU CLAVIER SI IL EXISTE DEJA",
                       settings.DARK_GRAY, cx, 60, scale)
        _draw_centered(surf, font, "PUIS VALIDE AVEC LA TOUCHE ENTREE",
                       settings.DARK_GRAY, cx, 70, scale)

        # Text input
        cursor = "_" if (self._tick // 30) % 2 == 0 else " "
        _draw_centered(surf, font, f"NOM : {self._name}{cursor}",
                       settings.WHITE, cx, 78, scale)

        # Existing students list
        if self._students:
            _draw_centered(surf, font, "--- élèves ---",
                           settings.DARK_GRAY, cx, 92, scale)
            for i, s in enumerate(self._students[:6]):
                color = (settings.COLOR_MENU_SELECT
                         if i == self._student_idx
                         else settings.COLOR_MENU_ITEM)
                _draw_centered(surf, font, s.upper(), color,
                               cx, 106 + i * 16, scale)

        _draw_centered(surf, font, "TAB : MODE ENSEIGNANT",
                       settings.DARK_GRAY, cx, lh - 40, scale)
        _draw_centered(surf, font, "ENTRÉE : CONFIRMER",
                       settings.DARK_GRAY, cx, lh - 28, scale)
        _draw_centered(surf, font, "ÉCHAP : QUITTER",
                       settings.DARK_GRAY, cx, lh - 16, scale)

        if self._confirming:
            box_w, box_h = 130, 14
            box_x = (cx - box_w // 2) * scale
            box_y = (lh // 2 - 3) * scale
            pygame.draw.rect(surf, (10, 30, 10),
                             (box_x, box_y, box_w * scale, box_h * scale))
            pygame.draw.rect(surf, settings.COLOR_MENU_TITLE,
                             (box_x, box_y, box_w * scale, box_h * scale), scale)
            _draw_centered(surf, font, "QUITTER ? (O/N)",
                           settings.COLOR_MENU_TITLE, cx, lh // 2, scale)


# ── Tournoi End Screen ─────────────────────────────────────────────────────────

class TournoiEndScreen:
    _VISIBLE = 10   # level rows visible at once

    def __init__(self, pack_name: str, level_scores: list, total_score: int):
        self._pack_name    = pack_name
        self._level_scores = level_scores
        self._total_score  = total_score
        self._scroll       = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_CONFIRM or event.key in settings.KEY_PAUSE:
            return 'back'
        if event.key in settings.KEY_UP:
            self._scroll = max(0, self._scroll - 1)
        elif event.key in settings.KEY_DOWN:
            max_scroll = max(0, len(self._level_scores) - self._VISIBLE)
            self._scroll = min(max_scroll, self._scroll + 1)
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        surf.fill(settings.COLOR_WIN_BG)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "TOURNOI TERMINÉ !",
                       settings.YELLOW, cx, 15, scale)
        _draw_centered(surf, font, self._pack_name.upper(),
                       settings.CYAN, cx, 30, scale)
        _draw_centered(surf, font, f"TOTAL : {self._total_score:5d} pts",
                       settings.WHITE, cx, 48, scale)
        _draw_centered(surf, font, "--- DÉTAIL ---",
                       settings.DARK_GRAY, cx, 65, scale)

        y0    = 80
        row_h = 12
        visible = self._level_scores[self._scroll:self._scroll + self._VISIBLE]
        for i, entry in enumerate(visible):
            lvl  = entry['level_idx'] + 1
            sc   = entry['score']
            att  = entry.get('attempts', 1)
            line = f"NV{lvl:02d}  {sc:4d} pts  x{att}"
            _draw_centered(surf, font, line, settings.WHITE,
                           cx, y0 + i * row_h, scale)

        # Scroll indicator when list overflows
        if len(self._level_scores) > self._VISIBLE:
            hi  = min(self._scroll + self._VISIBLE, len(self._level_scores))
            info = f"{self._scroll + 1}-{hi}/{len(self._level_scores)}"
            _draw_centered(surf, font, info, settings.DARK_GRAY,
                           cx, y0 + self._VISIBLE * row_h + 4, scale)

        _draw_centered(surf, font, "ENTRÉE : RETOUR",
                       settings.DARK_GRAY, cx, lh - 16, scale)


# ── Tournoi Intro Screen ───────────────────────────────────────────────────────

class TournoiIntroScreen:
    def __init__(self, pack_name: str):
        self._pack_name = pack_name
        self._tick      = 0

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_CONFIRM:
            return 'start'
        if event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        self._tick += 1
        _draw_trophy_bg(surf, font, self._tick, scale)
        lw, lh = settings.LOGICAL_W, settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "TOURNOI", (240, 200, 40), cx, 12, scale)
        _draw_centered(surf, font, self._pack_name.upper(), settings.CYAN, cx, 20, scale)

        lines = [
            "Utilise les flèches du clavier pour pousser les caisses sur les cases cibles",
            "en un minimum de mouvements !",
            "Tu peux annuler ton dernier mouvement en appuyant sur la touche U.",
            "",
            "Chaque niveau terminé te donne accès au suivant",
            "Il y a 20 niveaux au total",
            "",
            "Ton score dépendra de plusieurs critères :",
            "  - le nombre d'essais",
            "  - le nombre d'étapes",
            "  - le temps écoulé",
            "",
            "Tout est logique, il suffit de persévérer !",
            "Bonne chance et bon amusement !",
        ]
        y = 37
        for line in lines:
            _draw_centered(surf, font, line, settings.WHITE, cx, y, scale)
            y += 13

        # Pulsing prompt
        if (self._tick // 30) % 2 == 0:
            _draw_centered(surf, font, "ENTRÉE : commencer",
                           (220, 180, 0), cx, lh - 20, scale)
