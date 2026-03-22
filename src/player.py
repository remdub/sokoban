# src/player.py — Player position, facing direction, animation state

from __future__ import annotations
from typing import Tuple
import settings

DIR_NAMES = {
    ( 0, -1): 'up',
    ( 0,  1): 'down',
    (-1,  0): 'left',
    ( 1,  0): 'right',
}

FACE_RIGHT = 0
FACE_LEFT  = 1
FACE_DOWN  = 2
FACE_UP    = 3

DIR_TO_FACE = {
    ( 1,  0): FACE_RIGHT,
    (-1,  0): FACE_LEFT,
    ( 0,  1): FACE_DOWN,
    ( 0, -1): FACE_UP,
}


class Player:
    """
    Tracks the player's grid position, facing direction, and animation state.
    The renderer reads these values; the level module owns the authoritative
    grid position (player_pos). We mirror it here for rendering convenience.
    """

    def __init__(self, grid_x: int, grid_y: int):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.facing = FACE_DOWN         # which direction the sprite faces

        # Walk animation
        self._walk_timer  = 0           # frames since last step
        self._walk_frame  = 0           # 0-3 walk cycle
        self._is_walking  = False
        self._is_pushing  = False

        # Invalid-move shake
        self._shake_timer  = 0
        self.shake_offset  = (0, 0)     # pixel offset for screen shake

    # ── Sync from level state ─────────────────────────────────────────────────

    def sync(self, gx: int, gy: int, moved: bool, pushed: bool,
             dx: int = 0, dy: int = 0) -> None:
        self.grid_x = gx
        self.grid_y = gy
        if moved:
            if dx != 0 or dy != 0:
                self.facing = DIR_TO_FACE.get((dx, dy), self.facing)
            self._is_walking = True
            self._is_pushing = pushed
            self._walk_timer = settings.WALK_FRAME_DURATION
        else:
            self._is_walking = False
            self._is_pushing = False

    def trigger_invalid(self, dx: int, dy: int) -> None:
        """Start the screen-shake animation for an invalid move."""
        self._shake_timer = settings.SHAKE_FRAMES
        self.facing = DIR_TO_FACE.get((dx, dy), self.facing)

    # ── Per-frame update ──────────────────────────────────────────────────────

    def update(self) -> None:
        # Walk animation cycling
        if self._walk_timer > 0:
            self._walk_timer -= 1
            if self._walk_timer == 0:
                self._walk_frame = (self._walk_frame + 1) % 4
                self._is_walking = False

        # Screen shake
        if self._shake_timer > 0:
            self._shake_timer -= 1
            import math
            t = self._shake_timer
            amp = settings.SHAKE_AMPLITUDE
            self.shake_offset = (
                int(amp * math.sin(t * 1.8)),
                int(amp * math.cos(t * 2.1)),
            )
        else:
            self.shake_offset = (0, 0)

    # ── Properties for renderer ───────────────────────────────────────────────

    @property
    def walk_frame(self) -> int:
        return self._walk_frame if self._is_walking else 0

    @property
    def is_pushing(self) -> bool:
        return self._is_pushing

    @property
    def is_shaking(self) -> bool:
        return self._shake_timer > 0
