# src/replay.py — ReplayController: feeds a stored move log back into the game
from __future__ import annotations

from typing import List, Optional


class ReplayController:
    def __init__(self, move_log: List[str], speed: int = 10):
        self._log   = move_log
        self._pos   = 0
        self._speed = max(1, speed)
        self._frames_until_next = self._speed
        self._paused = False

    def tick(self) -> Optional[str]:
        """Call once per frame. Returns the next action code or None."""
        if self._paused or self._pos >= len(self._log):
            return None
        self._frames_until_next -= 1
        if self._frames_until_next <= 0:
            action = self._log[self._pos]
            self._pos += 1
            self._frames_until_next = self._speed
            return action
        return None

    def toggle_pause(self) -> None:
        self._paused = not self._paused

    def set_speed(self, frames_between: int) -> None:
        self._speed = max(1, frames_between)
        self._frames_until_next = min(self._frames_until_next, self._speed)

    @property
    def progress(self) -> float:
        if not self._log:
            return 1.0
        return self._pos / len(self._log)

    @property
    def is_done(self) -> bool:
        return self._pos >= len(self._log)

    def step_forward(self) -> Optional[str]:
        if not self._paused or self._pos >= len(self._log):
            return None
        action = self._log[self._pos]
        self._pos += 1
        self._frames_until_next = self._speed
        return action

    def reset(self) -> None:
        self._pos = 0
        self._frames_until_next = self._speed

    @property
    def paused(self) -> bool:
        return self._paused
