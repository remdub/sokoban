# src/student.py — Student profile load/save and attempt recording
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import settings


# ── Profile integrity (HMAC-SHA256) ──────────────────────────────────────────

def _hmac_key() -> bytes:
    return base64.b64decode(settings.STUDENT_HMAC_KEY_B64)


def _sign(data: dict) -> str:
    payload = {k: v for k, v in data.items() if k != '_sig'}
    serialised = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hmac.new(_hmac_key(), serialised.encode(), hashlib.sha256).hexdigest()


def _verify(data: dict) -> bool:
    expected = data.get('_sig', '')
    return hmac.compare_digest(expected, _sign(data))


def _profile_path(name: str) -> str:
    return os.path.join(settings.STUDENTS_DIR, f"{name}.json")


def list_students() -> List[str]:
    if not os.path.isdir(settings.STUDENTS_DIR):
        return []
    return [f[:-5] for f in os.listdir(settings.STUDENTS_DIR)
            if f.endswith('.json')]


def delete_student(name: str) -> None:
    path = _profile_path(name)
    if os.path.isfile(path):
        os.remove(path)


def load_profile(name: str) -> Dict:
    path = _profile_path(name)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not _verify(data):
            return {"name": name, "attempts": []}
        return data
    return {"name": name, "attempts": []}


def save_attempt(name: str, pack: str, level_idx: int,
                 completed: bool, moves: int, pushes: int,
                 time_sec: float, stars: int,
                 move_log: List[str],
                 game_type: str = "ENT", score: int = 0,
                 undos: int = 0) -> None:
    os.makedirs(settings.STUDENTS_DIR, exist_ok=True)
    profile = load_profile(name)
    profile["name"] = name
    profile.setdefault("attempts", []).append({
        "pack":       pack,
        "level_idx":  level_idx,
        "timestamp":  datetime.now().isoformat(timespec='seconds'),
        "completed":  completed,
        "moves":      moves,
        "pushes":     pushes,
        "time":       round(time_sec, 1),
        "stars":      stars,
        "game_type":  game_type,
        "score":      score,
        "undos":      undos,
        "move_log":   move_log,
    })
    _save_profile(profile)


def get_tournaments(name: str) -> List[Dict]:
    profile = load_profile(name)
    return profile.get("tournaments", [])


def get_attempts(name: str, pack: Optional[str] = None,
                 level_idx: Optional[int] = None) -> List[Dict]:
    profile = load_profile(name)
    attempts = profile.get("attempts", [])
    if pack is not None:
        attempts = [a for a in attempts if a.get("pack") == pack]
    if level_idx is not None:
        attempts = [a for a in attempts if a.get("level_idx") == level_idx]
    return attempts


def _save_profile(profile: dict) -> None:
    os.makedirs(settings.STUDENTS_DIR, exist_ok=True)
    profile['_sig'] = _sign(profile)
    with open(_profile_path(profile["name"]), 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def get_unlocked(name: str, pack_name: str) -> int:
    for pack in settings.LEVEL_PACKS:
        if pack['name'] == pack_name and pack.get('always_unlocked', False):
            return 9999
    profile = load_profile(name)
    return profile.get("packs", {}).get(pack_name, {}).get("unlocked", 1)


def unlock_level(name: str, pack_name: str, level_index: int) -> None:
    profile = load_profile(name)
    packs = profile.setdefault("packs", {})
    pack  = packs.setdefault(pack_name, {"unlocked": 1, "scores": {}})
    if level_index + 1 > pack.get("unlocked", 1):
        pack["unlocked"] = level_index + 1
    _save_profile(profile)


def record_score(name: str, pack_name: str, level_index: int,
                 moves: int, pushes: int, time_sec: float, stars: int) -> bool:
    """Returns True if new personal best."""
    profile = load_profile(name)
    packs   = profile.setdefault("packs", {})
    pack    = packs.setdefault(pack_name, {"unlocked": 1, "scores": {}})
    scores  = pack.setdefault("scores", {})
    key     = str(level_index)
    existing = scores.get(key)
    is_best  = False
    if existing is None or moves < existing['moves'] or (
            moves == existing['moves'] and pushes < existing['pushes']):
        scores[key] = {"moves": moves, "pushes": pushes,
                       "time": round(time_sec, 1), "stars": stars}
        is_best = True
    elif stars > existing.get('stars', 0):
        scores[key]['stars'] = stars
    _save_profile(profile)
    return is_best


def get_score(name: str, pack_name: str, level_index: int) -> dict:
    profile = load_profile(name)
    return (profile.get("packs", {})
                   .get(pack_name, {})
                   .get("scores", {})
                   .get(str(level_index), {}))


def save_tournament(name: str, pack: str, level_scores: list,
                    total_score: int) -> None:
    os.makedirs(settings.STUDENTS_DIR, exist_ok=True)
    profile = load_profile(name)
    profile["name"] = name
    profile.setdefault("tournaments", []).append({
        "timestamp":   datetime.now().isoformat(timespec='seconds'),
        "pack":        pack,
        "total_score": total_score,
        "levels":      level_scores,
    })
    _save_profile(profile)
