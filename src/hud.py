# src/hud.py — HUD drawing (moves, pushes, timer, level info)

from __future__ import annotations
import pygame
import settings


def draw(surface: pygame.Surface, font: pygame.font.Font,
         level_name: str, pack_name: str,
         level_index: int, level_total: int,
         moves: int, pushes: int,
         elapsed_sec: float, can_undo: bool,
         scale: int = 1, student_name: str = "",
         tournoi_attempt: int = 0) -> None:
    """
    Draw HUD bar at the bottom of the surface.
    Layout coordinates are in logical (320×240) units; multiply by scale before blitting.
    """
    lw = settings.LOGICAL_W
    lh = settings.LOGICAL_H
    bar_h = settings.HUD_HEIGHT

    # Semi-transparent background bar (scaled)
    bar_surf = pygame.Surface((lw * scale, bar_h * scale), pygame.SRCALPHA)
    bar_surf.fill((0, 0, 0, 200))
    surface.blit(bar_surf, (0, (lh - bar_h) * scale))

    y = lh - bar_h + 4

    # Level info — left side
    lv_str = f"NV{level_index + 1:02d}/{level_total:02d}"
    _draw_text(surface, font, lv_str, settings.COLOR_HIGHLIGHT, 2, y, scale)

    # Move / push counters — centre
    stat_str = f"D:{moves:03d} P:{pushes:03d}"
    cx = lw // 2
    _draw_text_centered(surface, font, stat_str, settings.COLOR_HUD_TEXT, cx, y, scale)

    # Timer — right side
    mins  = int(elapsed_sec) // 60
    secs  = int(elapsed_sec) % 60
    timer = f"{mins:02d}:{secs:02d}"
    _draw_text_right(surface, font, timer, settings.COLOR_HUD_TEXT, lw - 2, y, scale)

    # Undo / tournoi attempt indicator
    if tournoi_attempt > 0:
        _draw_text(surface, font, f"T:{tournoi_attempt}", settings.CYAN,
                   2, lh - bar_h - 10, scale)
    elif can_undo:
        _draw_text(surface, font, "A", settings.DARK_GRAY, 2, lh - bar_h - 10, scale)

    # Student name (right-aligned, same row as undo hint)
    if student_name:
        _draw_text_right(surface, font, student_name.upper(),
                         settings.DARK_GRAY, lw - 2, lh - bar_h - 10, scale)


def _draw_text(surface, font, text, color, x, y, scale=1):
    surf = font.render(text, False, color)
    surface.blit(surf, (x * scale, y * scale))


def _draw_text_centered(surface, font, text, color, cx, y, scale=1):
    surf = font.render(text, False, color)
    surface.blit(surf, (cx * scale - surf.get_width() // 2, y * scale))


def _draw_text_right(surface, font, text, color, rx, y, scale=1):
    surf = font.render(text, False, color)
    surface.blit(surf, (rx * scale - surf.get_width(), y * scale))
