# src/teacher_menu.py — Teacher-side UI screens (login, student list, detail)
from __future__ import annotations

import base64
import math
import os
from datetime import datetime
from typing import Dict, List, Optional

import pygame
import settings
import src.audio as audio
import src.student as student


# ── Shared helpers (mirror menu.py helpers to avoid import cycle) ─────────────

def _draw_text(surf, font, text, color, x, y, scale=1):
    s = font.render(text, False, color)
    surf.blit(s, (x * scale, y * scale))


def _draw_centered(surf, font, text, color, cx, y, scale=1):
    s = font.render(text, False, color)
    surf.blit(s, (cx * scale - s.get_width() // 2, y * scale))


# ── Report-card background constants ──────────────────────────────────────────
_CARD_BG     = (248, 240, 210)   # warm cream parchment
_CARD_LINE   = (200, 215, 235)   # faint blue ruled lines
_CARD_MARGIN = (200,  60,  60)   # red left margin line
_CARD_GLOW   = (255, 200,  50)   # golden border glow

_CARD_TITLE  = ( 20,  40, 120)   # dark school-blue title
_CARD_ITEM   = ( 30,  30,  80)   # dark blue item text
_CARD_SELECT = (180,  20,  20)   # red-pen selected highlight
_CARD_HINT   = (110, 100, 130)   # muted lavender-gray footer hints
_CARD_ERROR  = (200,   0,   0)   # bright red for errors

# Fixed star positions in logical coords (sx, sy)
_CARD_STARS  = [(10, 12), (310, 12), (10, 228), (310, 228),
                (160,  6), (24, 118), (296, 118)]


def _draw_report_card_bg(surf: pygame.Surface, scale: int = 1) -> None:
    lw = settings.LOGICAL_W
    lh = settings.LOGICAL_H

    # 1. Cream paper base
    surf.fill(_CARD_BG)

    # 2. Horizontal ruled lines every 12 logical px
    for y in range(12, lh, 12):
        pygame.draw.line(surf, _CARD_LINE,
                         (0, y * scale), (lw * scale, y * scale))

    # 3. Red left margin line at x=22
    pygame.draw.line(surf, _CARD_MARGIN,
                     (22 * scale, 0), (22 * scale, lh * scale),
                     max(1, scale // 2))

    # 4. Pulsing golden glow border
    t = pygame.time.get_ticks()
    pulse = int(12 * math.sin(t / 700.0))
    glow = pygame.Surface((lw * scale, lh * scale), pygame.SRCALPHA)
    for i in range(10):
        alpha = max(0, 55 - i * 5 + (pulse if i < 3 else 0))
        thickness = (10 - i) * scale
        r, g, b = _CARD_GLOW
        pygame.draw.rect(glow, (r, g, b, alpha),
                         (0, 0, lw * scale, lh * scale), thickness)
    surf.blit(glow, (0, 0))

    # 5. Twinkling gold stars near corners/margins
    for idx, (sx, sy) in enumerate(_CARD_STARS):
        phase = (t // 400 + idx * 3) % 6
        if phase < 3:
            brightness = 200 + int(55 * math.sin(t / 300.0 + idx))
            color = (brightness, int(brightness * 0.85), 0)
            sz = 2 * scale
            pygame.draw.rect(surf, color,
                             (sx * scale - sz // 2, sy * scale - sz // 2, sz, sz))


# ── PIN helper ────────────────────────────────────────────────────────────────

def check_pin(entered: str) -> bool:
    expected = base64.b64decode(settings.PROF_PIN_B64).decode()
    return entered == expected


# ── Teacher Login Screen ──────────────────────────────────────────────────────

class TeacherLoginScreen:
    def __init__(self):
        self._pin   = ""
        self._error = False

    def reset(self) -> None:
        self._pin   = ""
        self._error = False

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Returns 'login_ok', 'back', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if check_pin(self._pin):
                return 'login_ok'
            self._pin   = ""
            self._error = True
        elif event.key == pygame.K_BACKSPACE:
            self._pin   = self._pin[:-1]
            self._error = False
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        elif (event.unicode and event.unicode.isdigit()
              and len(self._pin) < 8):
            self._pin  += event.unicode
            self._error = False
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "ACCÈS ENSEIGNANT",
                       _CARD_TITLE, cx, 55, scale)

        masked = "*" * len(self._pin)
        _draw_centered(surf, font, f"CODE : {masked:<8}",
                       _CARD_ITEM, cx, 95, scale)
        if self._error:
            _draw_centered(surf, font, "CODE INCORRECT",
                           _CARD_ERROR, cx, 118, scale)

        _draw_centered(surf, font, "ENTRÉE : VALIDER  ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Student List Screen ───────────────────────────────────────────────

class TeacherStudentListScreen:
    def __init__(self):
        self._students: List[str] = []
        self._cursor = 0
        self._confirming = False

    def refresh(self) -> None:
        self._students = sorted(student.list_students())
        self._cursor   = 0
        self._confirming = False

    def handle_event(self, event: pygame.event.Event):
        """Returns a student name string, {'delete': name}, 'back', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if self._confirming:
            if event.key == pygame.K_o:
                self._confirming = False
                return {'delete': self._students[self._cursor]}
            elif event.key == pygame.K_n or event.key in settings.KEY_PAUSE:
                self._confirming = False
            return None
        if event.key in settings.KEY_UP:
            if self._cursor > 0:
                self._cursor -= 1
        elif event.key in settings.KEY_DOWN:
            if self._cursor < len(self._students) - 1:
                self._cursor += 1
        elif event.key in settings.KEY_CONFIRM:
            if self._students:
                return self._students[self._cursor]
        elif event.key == pygame.K_DELETE:
            if self._students:
                self._confirming = True
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, "ÉLÈVES", _CARD_TITLE,
                       cx, 12, scale)

        if not self._students:
            _draw_centered(surf, font, "Aucun élève enregistré",
                           _CARD_HINT, cx, 80, scale)
        else:
            for i, name in enumerate(self._students):
                color  = (_CARD_SELECT if i == self._cursor
                          else _CARD_ITEM)
                prefix = "> " if i == self._cursor else "  "
                _draw_centered(surf, font, prefix + name.upper(),
                               color, cx, 40 + i * 18, scale)

        if self._confirming:
            name = self._students[self._cursor]
            _draw_centered(surf, font, f"SUPPRIMER {name.upper()} ? (O/N)",
                           _CARD_ERROR, cx, lh - 20, scale)
        else:
            _draw_centered(surf, font,
                           "ENTRÉE : DÉTAIL   SUPPR : EFFACER   ÉCHAP : RETOUR",
                           _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Student Detail Screen ─────────────────────────────────────────────

class TeacherStudentDetailScreen:
    VISIBLE = 7   # max attempt rows shown at once

    def __init__(self, name: str, attempts: List[Dict]):
        self._name     = name
        self._attempts = attempts
        self._cursor   = 0 if attempts else -1
        self._scroll   = 0

    def handle_event(self, event: pygame.event.Event):
        """Returns {'action':'replay','attempt':...}, 'back', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            if self._cursor > 0:
                self._cursor -= 1
                if self._cursor < self._scroll:
                    self._scroll = self._cursor
        elif event.key in settings.KEY_DOWN:
            if self._cursor < len(self._attempts) - 1:
                self._cursor += 1
                if self._cursor >= self._scroll + self.VISIBLE:
                    self._scroll += 1
        elif event.key in settings.KEY_CONFIRM:
            if 0 <= self._cursor < len(self._attempts):
                attempt = self._attempts[self._cursor]
                if attempt.get('move_log'):
                    return {'action': 'replay', 'attempt': attempt}
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2

        _draw_centered(surf, font, self._name.upper(),
                       _CARD_TITLE, cx, 10, scale)

        if not self._attempts:
            _draw_centered(surf, font, "Aucune tentative",
                           _CARD_HINT, cx, 80, scale)
        else:
            # Header
            _draw_text(surf, font, "  TYPE            PACK          NIV    FAIT    MVTS  ANNUL   SCORE",
                       _CARD_HINT, 6, 30, scale)

            for row in range(self.VISIBLE):
                idx = self._scroll + row
                if idx >= len(self._attempts):
                    break
                a      = self._attempts[idx]
                is_sel = (idx == self._cursor)
                color  = (_CARD_SELECT if is_sel else _CARD_ITEM)

                typ    = a.get('game_type', 'ENT')
                pack_s = a.get('pack', '?')[:8]
                moves  = a.get('moves', 0)
                undos  = a.get('undos', 0)
                done   = "OUI" if a.get('completed') else "NON"
                lvl    = a.get('level_idx', 0) + 1
                if typ == "TRN":
                    score = a.get('score', 0)
                    line  = f"TOURNOI         {pack_s:<10}    {lvl:3d}    {done:>4}    {moves:4d}  {undos:5d}   {score:5d}"
                else:
                    line  = f"ENTRAINEMENT    {pack_s:<10}    {lvl:3d}    {done:>4}    {moves:4d}  {undos:5d}       -"
                prefix = "> " if is_sel else "  "
                _draw_text(surf, font, prefix + line,
                           color, 6, 42 + row * 18, scale)

            # Timestamp for selected attempt
            if 0 <= self._cursor < len(self._attempts):
                ts_raw = self._attempts[self._cursor].get('timestamp', '')
                if ts_raw:
                    ts = ts_raw.replace('T', ' ')[:16]
                    _draw_centered(surf, font, f"Joué le : {ts}",
                                   _CARD_HINT, cx, 42 + self.VISIBLE * 18 + 4, scale)

            # Scroll indicator
            if len(self._attempts) > self.VISIBLE:
                shown = f"{self._scroll+1}-{min(self._scroll+self.VISIBLE, len(self._attempts))}/{len(self._attempts)}"
                _draw_centered(surf, font, shown,
                               _CARD_HINT, cx, lh - 32, scale)

        hint = "ENTRÉE : REJOUER  ÉCHAP : RETOUR"
        _draw_centered(surf, font, hint, _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Tournoi List Screen ───────────────────────────────────────────────

class TeacherTournoiListScreen:
    VISIBLE = 7

    def __init__(self, name: str, tournaments: list):
        self._name        = name
        self._tournaments = sorted(tournaments,
                                   key=lambda t: t.get('timestamp', ''), reverse=True)
        self._cursor = 0 if tournaments else -1
        self._scroll = 0

    def handle_event(self, event: pygame.event.Event):
        """Returns {'action':'view_detail','tournament':...}, 'back', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            if self._cursor > 0:
                self._cursor -= 1
                if self._cursor < self._scroll:
                    self._scroll = self._cursor
        elif event.key in settings.KEY_DOWN:
            if self._cursor < len(self._tournaments) - 1:
                self._cursor += 1
                if self._cursor >= self._scroll + self.VISIBLE:
                    self._scroll += 1
        elif event.key in settings.KEY_CONFIRM:
            if 0 <= self._cursor < len(self._tournaments):
                return {'action': 'view_detail',
                        'tournament': self._tournaments[self._cursor]}
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        _draw_centered(surf, font, f"TOURNOIS — {self._name.upper()}",
                       _CARD_TITLE, cx, 10, scale)
        if not self._tournaments:
            _draw_centered(surf, font, "Aucun tournoi", _CARD_HINT, cx, 80, scale)
        else:
            _draw_text(surf, font,
                       "  DATE & HEURE       PACK            SCORE",
                       _CARD_HINT, 6, 30, scale)
            for row in range(self.VISIBLE):
                idx = self._scroll + row
                if idx >= len(self._tournaments):
                    break
                t      = self._tournaments[idx]
                is_sel = (idx == self._cursor)
                color  = _CARD_SELECT if is_sel else _CARD_ITEM
                ts     = t.get('timestamp', '')[:16].replace('T', ' ')
                pack_s = t.get('pack', '?')[:10]
                total  = t.get('total_score', 0)
                line   = f"{ts}  {pack_s:<12}  {total:6d}"
                prefix = "> " if is_sel else "  "
                _draw_text(surf, font, prefix + line, color, 6, 42 + row * 18, scale)
            if len(self._tournaments) > self.VISIBLE:
                shown = (f"{self._scroll+1}-"
                         f"{min(self._scroll+self.VISIBLE, len(self._tournaments))}/"
                         f"{len(self._tournaments)}")
                _draw_centered(surf, font, shown, _CARD_HINT, cx, lh - 32, scale)
        _draw_centered(surf, font, "ENTRÉE : DÉTAILS  ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Tournoi Detail Screen ─────────────────────────────────────────────

class TeacherTournoiDetailScreen:
    VISIBLE = 8

    def __init__(self, tournament: dict):
        self._tournament = tournament
        self._levels     = tournament.get('levels', [])
        self._scroll     = 0

    def handle_event(self, event: pygame.event.Event):
        """Returns 'back' or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            if self._scroll > 0:
                self._scroll -= 1
        elif event.key in settings.KEY_DOWN:
            if self._scroll + self.VISIBLE < len(self._levels):
                self._scroll += 1
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        pack_s = self._tournament.get('pack', '?')
        ts     = self._tournament.get('timestamp', '')[:16].replace('T', ' ')
        total  = self._tournament.get('total_score', 0)
        _draw_centered(surf, font, f"{pack_s.upper()} — {ts}", _CARD_TITLE, cx, 10, scale)
        _draw_centered(surf, font, f"TOTAL : {total} pts", _CARD_ITEM, cx, 22, scale)
        if not self._levels:
            _draw_centered(surf, font, "Aucun niveau", _CARD_HINT, cx, 80, scale)
        else:
            _draw_text(surf, font,
                       "  NIV    SCORE    MVTS  ESSAIS    TEMPS",
                       _CARD_HINT, 6, 36, scale)
            for row in range(self.VISIBLE):
                idx = self._scroll + row
                if idx >= len(self._levels):
                    break
                lv      = self._levels[idx]
                lvl_num = lv.get('level_idx', idx) + 1
                score   = lv.get('score', 0)
                moves   = lv.get('moves', 0)
                att     = lv.get('attempts', 1)
                time_s  = lv.get('time', 0.0)
                line    = f"  {lvl_num:3d}   {score:5d}   {moves:4d}  {att:6d}   {time_s:6.1f}s"
                _draw_text(surf, font, line, _CARD_ITEM, 6, 48 + row * 18, scale)
            if len(self._levels) > self.VISIBLE:
                shown = (f"{self._scroll+1}-"
                         f"{min(self._scroll+self.VISIBLE, len(self._levels))}/"
                         f"{len(self._levels)}")
                _draw_centered(surf, font, shown, _CARD_HINT, cx, lh - 32, scale)
        _draw_centered(surf, font, "ÉCHAP : RETOUR", _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Student Sub-Menu ──────────────────────────────────────────────────

class TeacherStudentSubMenu:
    ITEMS = [
        ("REPLAY DES PARTIES", "detail"),
        ("STATS DES TOURNOIS",  "tournois"),
    ]

    def __init__(self, name: str):
        self._name     = name
        self._selected = 0

    def handle_event(self, event: pygame.event.Event):
        """Returns 'detail', 'tournois', 'back', or None."""
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
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        _draw_centered(surf, font, self._name.upper(), _CARD_TITLE, cx, 30, scale)
        for i, (label, _) in enumerate(self.ITEMS):
            color  = _CARD_SELECT if i == self._selected else _CARD_ITEM
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + label, color, cx, 80 + i * 24, scale)
        _draw_centered(surf, font, "FLÈCHES   ENTRÉE   ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Home Screen ───────────────────────────────────────────────────────

def _get_class_tournoi_stats(pack_name: str) -> dict:
    """Aggregate tournament data across all students for a given pack.

    Returns {'ranking': [(name, best_score, run_count), ...],
             'levels':  {level_idx: {avg_score, avg_attempts, avg_time}}}
    """
    ranking: list = []
    level_buckets: dict = {}
    for name in student.list_students():
        tournois = [t for t in student.get_tournaments(name)
                    if t.get('pack') == pack_name]
        if not tournois:
            continue
        best = max(tournois, key=lambda t: t.get('total_score', 0))
        ranking.append((name, best['total_score'], len(tournois)))
        for lv in best.get('levels', []):
            idx = lv.get('level_idx', 0)
            b = level_buckets.setdefault(
                idx, {'scores': [], 'attempts': [], 'times': []})
            b['scores'].append(lv.get('score', 0))
            b['attempts'].append(lv.get('attempts', 1))
            b['times'].append(lv.get('time', 0.0))
    ranking.sort(key=lambda x: x[1], reverse=True)
    levels = {
        idx: {
            'avg_score':    round(sum(b['scores'])   / len(b['scores'])),
            'avg_attempts': round(sum(b['attempts'])  / len(b['attempts']), 1),
            'avg_time':     round(sum(b['times'])     / len(b['times']), 1),
        }
        for idx, b in level_buckets.items()
    }
    return {'ranking': ranking, 'levels': levels}


# ── Teacher Tournoi Classe Pack Screen ────────────────────────────────────────

class TeacherTournoiClassePackScreen:
    def __init__(self):
        self._packs = [p['name'] for p in settings.LEVEL_PACKS]
        self._cursor = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Returns a pack name, 'back', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_UP:
            self._cursor = (self._cursor - 1) % len(self._packs)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_DOWN:
            self._cursor = (self._cursor + 1) % len(self._packs)
            audio.play_sfx('move.wav')
        elif event.key in settings.KEY_CONFIRM:
            return self._packs[self._cursor]
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        _draw_centered(surf, font, "STATS CLASSE — CHOISIR PACK",
                       _CARD_TITLE, cx, 30, scale)
        for i, name in enumerate(self._packs):
            color  = _CARD_SELECT if i == self._cursor else _CARD_ITEM
            prefix = "> " if i == self._cursor else "  "
            _draw_centered(surf, font, prefix + name.upper(),
                           color, cx, 70 + i * 20, scale)
        _draw_centered(surf, font, "FLÈCHES   ENTRÉE   ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Tournoi Classe Stats Screen ───────────────────────────────────────

class TeacherTournoiClasseScreen:
    VISIBLE = 7

    def __init__(self, pack_name: str, stats: dict):
        self._pack    = pack_name
        self._ranking = stats['ranking']   # [(name, best_score, run_count)]
        self._levels  = stats['levels']    # {level_idx: {avg_score, ...}}
        self._view    = 'ranking'          # 'ranking' or 'levels'
        self._scroll  = 0
        self._sorted_levels = sorted(self._levels.items())  # [(idx, data)]

    def _max_scroll(self) -> int:
        count = (len(self._ranking) if self._view == 'ranking'
                 else len(self._sorted_levels))
        return max(0, count - self.VISIBLE)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Returns 'back' or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in settings.KEY_LEFT:
            self._view   = 'ranking'
            self._scroll = 0
        elif event.key in settings.KEY_RIGHT:
            self._view   = 'levels'
            self._scroll = 0
        elif event.key in settings.KEY_UP:
            if self._scroll > 0:
                self._scroll -= 1
        elif event.key in settings.KEY_DOWN:
            if self._scroll < self._max_scroll():
                self._scroll += 1
        elif event.key in settings.KEY_PAUSE:
            return 'back'
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2

        _draw_centered(surf, font,
                       f"STATS CLASSE — {self._pack.upper()}",
                       _CARD_TITLE, cx, 10, scale)

        # Tab line
        if self._view == 'ranking':
            tab = "< CLASSEMENT >  |  PAR NIVEAU"
        else:
            tab = "CLASSEMENT  |  < PAR NIVEAU >"
        _draw_centered(surf, font, tab, _CARD_HINT, cx, 22, scale)

        if self._view == 'ranking':
            self._draw_ranking(surf, font, scale)
        else:
            self._draw_levels(surf, font, scale)

        _draw_centered(surf, font,
                       "GAUCHE / DROITE : CHANGER VUE   HAUT / BAS : DÉFILER   ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)

    def _draw_ranking(self, surf: pygame.Surface, font: pygame.font.Font,
                      scale: int) -> None:
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        if not self._ranking:
            _draw_centered(surf, font, "Aucun tournoi pour ce pack",
                           _CARD_HINT, cx, 90, scale)
            return
        _draw_text(surf, font, "   #  NOM              SCORE  RUNS",
                   _CARD_HINT, 6, 36, scale)
        for row in range(self.VISIBLE):
            idx = self._scroll + row
            if idx >= len(self._ranking):
                break
            name, best, runs = self._ranking[idx]
            line = f"  {idx+1:2d}  {name[:12].upper():<12}  {best:6d}   {runs:2d}"
            _draw_text(surf, font, line, _CARD_ITEM, 6, 48 + row * 18, scale)
        if len(self._ranking) > self.VISIBLE:
            shown = (f"{self._scroll+1}-"
                     f"{min(self._scroll+self.VISIBLE, len(self._ranking))}/"
                     f"{len(self._ranking)}")
            _draw_centered(surf, font, shown, _CARD_HINT, cx, lh - 32, scale)

    def _draw_levels(self, surf: pygame.Surface, font: pygame.font.Font,
                     scale: int) -> None:
        lh = settings.LOGICAL_H
        cx = settings.LOGICAL_W // 2
        if not self._sorted_levels:
            _draw_centered(surf, font, "Aucune donnée",
                           _CARD_HINT, cx, 90, scale)
            return
        _draw_text(surf, font, "  NIV  MOY.SCORE  MOY.ESSAIS  MOY.TEMPS",
                   _CARD_HINT, 6, 36, scale)
        for row in range(self.VISIBLE):
            idx = self._scroll + row
            if idx >= len(self._sorted_levels):
                break
            level_idx, data = self._sorted_levels[idx]
            line = (f"  {level_idx+1:3d}  {data['avg_score']:9d}"
                    f"  {data['avg_attempts']:10.1f}"
                    f"  {data['avg_time']:7.1f}s")
            _draw_text(surf, font, line, _CARD_ITEM, 6, 48 + row * 18, scale)
        if len(self._sorted_levels) > self.VISIBLE:
            shown = (f"{self._scroll+1}-"
                     f"{min(self._scroll+self.VISIBLE, len(self._sorted_levels))}/"
                     f"{len(self._sorted_levels)}")
            _draw_centered(surf, font, shown, _CARD_HINT, cx, lh - 32, scale)


# ── Teacher Home Screen ───────────────────────────────────────────────────────

class TeacherHomeScreen:
    ITEMS = [
        ("GESTION DES ÉLÈVES",       "students"),
        ("STATS CLASSE TOURNOI",     "classe"),
        ("EXPORTER STATS TOURNOI",   "export"),
        ("OPTIONS",                  "options"),
    ]

    def __init__(self):
        self._selected = 0

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
             scale: int = 1) -> None:
        _draw_report_card_bg(surf, scale)
        lw = settings.LOGICAL_W
        lh = settings.LOGICAL_H
        cx = lw // 2
        _draw_centered(surf, font, "MENU ENSEIGNANT", _CARD_TITLE,
                       cx, 30, scale)
        for i, (label, _) in enumerate(self.ITEMS):
            color  = (_CARD_SELECT if i == self._selected else _CARD_ITEM)
            prefix = "> " if i == self._selected else "  "
            _draw_centered(surf, font, prefix + label, color, cx,
                           80 + i * 24, scale)
        _draw_centered(surf, font, "FLÈCHES   ENTRÉE   ÉCHAP : RETOUR",
                       _CARD_HINT, cx, lh - 20, scale)


# ── Teacher Menu (manages list + detail sub-screens) ──────────────────────────

class TeacherMenu:
    def __init__(self):
        self._home            = TeacherHomeScreen()
        self._list            = TeacherStudentListScreen()
        self._submenu:         Optional[TeacherStudentSubMenu]          = None
        self._detail:          Optional[TeacherStudentDetailScreen]     = None
        self._tournoi_list:    Optional[TeacherTournoiListScreen]       = None
        self._tournoi_detail:  Optional[TeacherTournoiDetailScreen]     = None
        self._classe_pack:     Optional[TeacherTournoiClassePackScreen] = None
        self._classe_stats:    Optional[TeacherTournoiClasseScreen]     = None
        self._mode          = 'home'
        self._export_msg:   str = ''
        self._export_timer: int = 0

    def refresh(self) -> None:
        self._list.refresh()
        self._home._selected  = 0
        self._submenu         = None
        self._detail          = None
        self._tournoi_list    = None
        self._tournoi_detail  = None
        self._classe_pack     = None
        self._classe_stats    = None
        self._mode            = 'home'

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        """Returns {'action':'exit'}, {'action':'options'}, {'action':'replay','attempt':...}, or None."""
        if self._mode == 'home':
            action = self._home.handle_event(event)
            if action == 'back':
                return {'action': 'exit'}
            elif action == 'students':
                self._mode = 'list'
            elif action == 'options':
                return {'action': 'options'}
            elif action == 'export':
                ts   = datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join(os.path.dirname(settings.STUDENTS_DIR),
                                    f"export_{ts}.csv")
                n = student.export_tournament_csv(path)
                if n:
                    self._export_msg = f"Exporté: export_{ts}.csv ({n} lignes)"
                else:
                    self._export_msg = "Aucune donnée à exporter"
                self._export_timer = 180
            elif action == 'classe':
                self._classe_pack = TeacherTournoiClassePackScreen()
                self._mode        = 'classe_pack'
        elif self._mode == 'classe_pack' and self._classe_pack:
            action = self._classe_pack.handle_event(event)
            if action == 'back':
                self._mode        = 'home'
                self._classe_pack = None
            elif isinstance(action, str):
                stats = _get_class_tournoi_stats(action)
                self._classe_stats = TeacherTournoiClasseScreen(action, stats)
                self._mode         = 'classe_stats'
        elif self._mode == 'classe_stats' and self._classe_stats:
            action = self._classe_stats.handle_event(event)
            if action == 'back':
                self._mode         = 'classe_pack'
                self._classe_stats = None
        elif self._mode == 'list':
            action = self._list.handle_event(event)
            if action == 'back':
                self._mode = 'home'
            elif isinstance(action, dict) and action.get('delete'):
                student.delete_student(action['delete'])
                self._list.refresh()
            elif isinstance(action, str):
                self._submenu = TeacherStudentSubMenu(action)
                self._mode    = 'student_submenu'
        elif self._mode == 'student_submenu' and self._submenu:
            action = self._submenu.handle_event(event)
            if action == 'back':
                self._mode    = 'list'
                self._submenu = None
            elif action == 'detail':
                name     = self._submenu._name
                attempts = sorted(student.get_attempts(name),
                                  key=lambda a: a.get('timestamp', ''), reverse=True)
                self._detail = TeacherStudentDetailScreen(name, attempts)
                self._mode   = 'detail'
            elif action == 'tournois':
                name     = self._submenu._name
                tournois = student.get_tournaments(name)
                self._tournoi_list = TeacherTournoiListScreen(name, tournois)
                self._mode         = 'tournoi_list'
        elif self._mode == 'detail' and self._detail:
            action = self._detail.handle_event(event)
            if action == 'back':
                self._mode   = 'student_submenu'
                self._detail = None
            elif isinstance(action, dict):
                return action  # replay request
        elif self._mode == 'tournoi_list' and self._tournoi_list:
            action = self._tournoi_list.handle_event(event)
            if action == 'back':
                self._mode         = 'student_submenu'
                self._tournoi_list = None
            elif isinstance(action, dict) and action.get('action') == 'view_detail':
                self._tournoi_detail = TeacherTournoiDetailScreen(action['tournament'])
                self._mode           = 'tournoi_detail'
        elif self._mode == 'tournoi_detail' and self._tournoi_detail:
            action = self._tournoi_detail.handle_event(event)
            if action == 'back':
                self._mode           = 'tournoi_list'
                self._tournoi_detail = None
        return None

    def draw(self, surf: pygame.Surface, font: pygame.font.Font,
             scale: int = 1) -> None:
        if self._mode == 'home':
            self._home.draw(surf, font, scale)
        elif self._mode == 'list':
            self._list.draw(surf, font, scale)
        elif self._mode == 'student_submenu' and self._submenu:
            self._submenu.draw(surf, font, scale)
        elif self._mode == 'detail' and self._detail:
            self._detail.draw(surf, font, scale)
        elif self._mode == 'tournoi_list' and self._tournoi_list:
            self._tournoi_list.draw(surf, font, scale)
        elif self._mode == 'tournoi_detail' and self._tournoi_detail:
            self._tournoi_detail.draw(surf, font, scale)
        elif self._mode == 'classe_pack' and self._classe_pack:
            self._classe_pack.draw(surf, font, scale)
        elif self._mode == 'classe_stats' and self._classe_stats:
            self._classe_stats.draw(surf, font, scale)
        if self._export_timer > 0:
            _draw_centered(surf, font, self._export_msg, _CARD_SELECT,
                           settings.LOGICAL_W // 2, settings.LOGICAL_H - 10, scale)
            self._export_timer -= 1
