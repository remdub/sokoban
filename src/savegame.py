# src/savegame.py — JSON save/load beside executable

from __future__ import annotations
import json
import os
from typing import Dict, Any
import settings


_DEFAULT_SAVE: Dict[str, Any] = {
    "version": 1,
    "sfx_volume": settings.DEFAULT_SFX_VOLUME,
    "music_volume": settings.DEFAULT_MUSIC_VOLUME,
    "crt_enabled": True,
    "fullscreen": False,
    "current_pack": 0,
    "current_level": 0,
}

_save: Dict[str, Any] = {}


def load() -> None:
    """Load save.json; falls back to defaults on any error."""
    global _save
    _save = dict(_DEFAULT_SAVE)
    try:
        if os.path.exists(settings.SAVE_PATH):
            with open(settings.SAVE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Merge loaded data over defaults so new keys always exist
            _save.update(data)
    except Exception:
        pass


def save() -> None:
    """Persist current save state to disk."""
    try:
        with open(settings.SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_save, f, indent=2)
    except Exception:
        pass


def get(key: str, default=None):
    return _save.get(key, default)


def set(key: str, value) -> None:
    _save[key] = value


def compute_stars(moves: int, optimal: int) -> int:
    if optimal <= 0:
        return 1  # unknown optimal → give 1 star just for finishing
    if moves <= optimal * settings.STAR_3_MULTIPLIER:
        return 3
    if moves <= optimal * settings.STAR_2_MULTIPLIER:
        return 2
    if moves <= optimal * settings.STAR_1_MULTIPLIER:
        return 1
    return 1


def compute_tournoi_level_score(moves: int, attempts: int,
                                time_sec: float, optimal: int,
                                undos: int = 0) -> int:
    if optimal <= 0:
        optimal = moves
    move_ratio   = min(1.0, optimal / max(1, moves))
    moves_pts    = int(move_ratio * settings.TOURNOI_MOVES_MAX)
    attempts_pts = max(0, settings.TOURNOI_ATTEMPTS_MAX
                       - (attempts - 1) * settings.TOURNOI_ATTEMPTS_PEN)
    time_pts     = max(0, settings.TOURNOI_TIME_MAX - int(time_sec))
    undo_pen     = undos * settings.TOURNOI_UNDO_PEN
    return max(0, moves_pts + attempts_pts + time_pts - undo_pen)
