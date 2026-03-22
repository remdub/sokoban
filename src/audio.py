# src/audio.py — Sound/music manager with graceful no-op on failure

from __future__ import annotations
import os
import settings

_mixer_ok   = False
_sfx_cache  = {}
_current_music = None
_sfx_volume  = settings.DEFAULT_SFX_VOLUME
_music_volume = settings.DEFAULT_MUSIC_VOLUME


def init() -> bool:
    """Initialize pygame.mixer. Returns True on success."""
    global _mixer_ok
    try:
        import pygame
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        _mixer_ok = True
    except Exception:
        _mixer_ok = False
    return _mixer_ok


def _sfx_path(name: str) -> str:
    return os.path.join(settings.ASSETS_DIR, 'sounds', name)


def play_sfx(name: str) -> None:
    """Play a sound effect by filename (e.g. 'move.wav')."""
    if not _mixer_ok:
        return
    try:
        import pygame
        if name not in _sfx_cache:
            path = _sfx_path(name)
            if not os.path.exists(path):
                return
            _sfx_cache[name] = pygame.mixer.Sound(path)
        snd = _sfx_cache[name]
        snd.set_volume(_sfx_volume)
        snd.play()
    except Exception:
        pass


def play_music(name: str, loops: int = -1) -> None:
    """Play background music by filename (e.g. 'music_menu.ogg')."""
    global _current_music
    if not _mixer_ok:
        return
    if name == _current_music:
        return
    try:
        import pygame
        path = _sfx_path(name)
        if not os.path.exists(path):
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(loops)
        _current_music = name
    except Exception:
        pass


def stop_music() -> None:
    global _current_music
    if not _mixer_ok:
        return
    try:
        import pygame
        pygame.mixer.music.stop()
        _current_music = None
    except Exception:
        pass


def set_sfx_volume(vol: float) -> None:
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, vol))


def set_music_volume(vol: float) -> None:
    global _music_volume
    _music_volume = max(0.0, min(1.0, vol))
    if not _mixer_ok:
        return
    try:
        import pygame
        pygame.mixer.music.set_volume(_music_volume)
    except Exception:
        pass


def get_sfx_volume() -> float:
    return _sfx_volume


def get_music_volume() -> float:
    return _music_volume
