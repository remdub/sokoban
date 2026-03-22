# src/history.py — Undo/redo stack using command pattern

from __future__ import annotations
from typing import List, Optional
from src.level import MoveResult
import settings


class History:
    """
    Stores MoveResults so the level can be rewound.
    Capped at MAX_HISTORY entries; oldest entries are dropped when full.
    """

    def __init__(self):
        self._undo_stack: List[MoveResult] = []
        self._redo_stack: List[MoveResult] = []

    def push(self, result: MoveResult) -> None:
        """Record a successful move. Clears redo stack."""
        if not result.moved:
            return
        self._undo_stack.append(result)
        if len(self._undo_stack) > settings.MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def undo(self) -> Optional[MoveResult]:
        """Return the last MoveResult to be un-applied, or None."""
        if not self._undo_stack:
            return None
        result = self._undo_stack.pop()
        self._redo_stack.append(result)
        return result

    def redo(self) -> Optional[MoveResult]:
        """Return the next MoveResult to be re-applied, or None."""
        if not self._redo_stack:
            return None
        result = self._redo_stack.pop()
        self._undo_stack.append(result)
        return result

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)
