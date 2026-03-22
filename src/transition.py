# src/transition.py — Screen transitions (pixelate wipe, scanline wipe)

from __future__ import annotations
from typing import Optional
import pygame
import settings

TRANSITION_FRAMES = 18   # ~0.3 s at 60 fps


class Transition:
    """
    Captures the outgoing frame, then animates over TRANSITION_FRAMES frames.
    The caller is responsible for blitting the new scene underneath.
    """

    def __init__(self):
        self._active  = False
        self._timer   = 0
        self._surface: Optional[pygame.Surface] = None
        self._style   = 'pixelate'    # 'pixelate' | 'scanwipe'

    def start(self, outgoing_surface: pygame.Surface, style: str = 'pixelate') -> None:
        self._surface = outgoing_surface.copy()
        self._timer   = TRANSITION_FRAMES
        self._active  = True
        self._style   = style

    @property
    def active(self) -> bool:
        return self._active

    def update(self) -> None:
        if self._active:
            self._timer -= 1
            if self._timer <= 0:
                self._active  = False
                self._surface = None

    def draw(self, dest: pygame.Surface) -> None:
        """Blit the transition overlay onto dest."""
        if not self._active or self._surface is None:
            return

        progress = 1.0 - self._timer / TRANSITION_FRAMES   # 0 → 1

        if self._style == 'pixelate':
            self._draw_pixelate(dest, progress)
        else:
            self._draw_scanwipe(dest, progress)

    def _draw_pixelate(self, dest: pygame.Surface, progress: float) -> None:
        """Scale surface down then up to create pixelation effect."""
        alpha = int(255 * (1.0 - progress))
        if alpha <= 0:
            return

        w, h = self._surface.get_size()
        # Reduce resolution by progress
        scale = max(1, int(1 + progress * 16))
        small_w = max(1, w // scale)
        small_h = max(1, h // scale)

        try:
            small = pygame.transform.scale(self._surface, (small_w, small_h))
            big   = pygame.transform.scale(small, (w, h))
            big.set_alpha(alpha)
            dest.blit(big, (0, 0))
        except Exception:
            pass

    def _draw_scanwipe(self, dest: pygame.Surface, progress: float) -> None:
        """Scanline-wipe: reveal new scene through horizontal stripes."""
        alpha = int(255 * (1.0 - progress))
        if alpha <= 0:
            return
        self._surface.set_alpha(alpha)
        dest.blit(self._surface, (0, 0))
