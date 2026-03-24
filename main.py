#!/usr/bin/env python3
# main.py — Entry point, game loop, state machine
#
# States: PROFILE_SELECT | MENU | LEVEL_SELECT | OPTIONS | PLAYING |
#         PAUSED | WIN | PROF_LOGIN | PROF_MENU | REPLAY
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

import pygame

import settings
import src.audio    as audio
import src.savegame as savegame
import src.student  as student
from src.level        import load_pack, Level
from src.player       import Player
from src.renderer     import Renderer
from src.history      import History
from src.transition   import Transition
from src.replay       import ReplayController
from src.menu         import (MainMenu, EntrainementMenu, LevelSelect, PauseScreen,
                               WinScreen, OptionsScreen, ProfileSelectScreen,
                               TournoiPackSelectScreen, TournoiEndScreen,
                               TournoiIntroScreen)
from src.teacher_menu import TeacherLoginScreen, TeacherMenu
import src.hud as hud


# ── Game State ────────────────────────────────────────────────────────────────

class GameState:
    PROFILE_SELECT      = 'profile_select'
    MENU                = 'menu'
    LEVEL_SELECT        = 'level_select'
    OPTIONS             = 'options'
    PLAYING             = 'playing'
    PAUSED              = 'paused'
    WIN                 = 'win'
    PROF_LOGIN          = 'prof_login'
    PROF_MENU           = 'prof_menu'
    REPLAY              = 'replay'
    TOURNOI_PACK_SELECT = 'tournoi_pack_select'
    TOURNOI_INTRO       = 'tournoi_intro'
    TOURNOI_END         = 'tournoi_end'
    ENTRAINEMENT_MENU   = 'entrainement_menu'


# ── Font loader ───────────────────────────────────────────────────────────────

def load_font(size: int) -> pygame.font.Font:
    """Return pygame's built-in bitmap font at the given size (window pixels)."""
    return pygame.font.Font(None, size)


# ── Main game ─────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()

        # Audio (graceful failure)
        audio.init()

        # Save data
        savegame.load()
        audio.set_sfx_volume(savegame.get('sfx_volume', settings.DEFAULT_SFX_VOLUME))
        audio.set_music_volume(savegame.get('music_volume', settings.DEFAULT_MUSIC_VOLUME))

        # Window — start windowed; may go fullscreen per options
        flags = 0
        if savegame.get('fullscreen', False):
            flags = pygame.FULLSCREEN
        self.window = pygame.display.set_mode(
            (settings.WINDOW_W, settings.WINDOW_H), flags)
        pygame.display.set_caption(settings.WINDOW_TITLE)

        # Logical 320×240 surface — all game drawing happens here
        self.logical = pygame.Surface((settings.LOGICAL_W, settings.LOGICAL_H))

        self.clock     = pygame.time.Clock()
        self.font_sm   = load_font(18)   # HUD text (window pixels, post-scale)
        self.font_md   = load_font(24)   # menu body text

        # Renderer
        self.renderer  = Renderer(self.logical)
        self.renderer.set_crt(savegame.get('crt_enabled', True))

        # Transition
        self.transition = Transition()

        # Menus
        self.profile_select_screen = ProfileSelectScreen()
        self.main_menu             = MainMenu()
        self.entrainement_menu     = EntrainementMenu()
        self.pause_screen          = PauseScreen()
        self.win_screen            = WinScreen()
        self.options_screen        = OptionsScreen()
        self.teacher_login         = TeacherLoginScreen()
        self.teacher_menu          = TeacherMenu()
        self.tournoi_pack_select   = TournoiPackSelectScreen()
        self.tournoi_end_screen: TournoiEndScreen | None = None

        # Level packs — loaded lazily
        self._packs: list = [None] * len(settings.LEVEL_PACKS)
        self.level_select = LevelSelect(
            [p['name'] for p in settings.LEVEL_PACKS])

        # Game session variables
        self.state        = GameState.PROFILE_SELECT
        self.current_pack = savegame.get('current_pack', 0)
        self.current_lvl_idx = savegame.get('current_level', 0)
        self.level: Level | None     = None
        self.player: Player | None   = None
        self.history      = History()

        self.moves        = 0
        self.pushes       = 0
        self._start_time  = 0.0
        self._elapsed     = 0.0

        self._win_is_best = False
        self._win_stars   = 0

        # Tournoi session
        self._tournoi_mode:       bool      = False
        self._tournoi_pack:       int       = 0
        self._tournoi_attempt:    int       = 1
        self._tournoi_scores:     list      = []
        self._tournoi_session_ts: str       = ''
        self._win_tournoi_score: int | None = None
        self._pending_tournoi_pack: int     = 0
        self.tournoi_intro_screen: TournoiIntroScreen | None = None

        # Student / teacher / replay
        self.student_name: str              = ""
        self._move_log: list                = []
        self._replay_ctrl: ReplayController | None = None
        self._replay_attempt: dict          = {}
        self._is_replay: bool               = False

        # Prepare profile select
        self.profile_select_screen.refresh()

        audio.play_music('music_menu.ogg')

    # ── Level pack lazy loading ───────────────────────────────────────────────

    def _ensure_pack(self, idx: int) -> list:
        if self._packs[idx] is None:
            try:
                self._packs[idx] = load_pack(settings.LEVEL_PACKS[idx])
            except Exception as e:
                print(f"Warning: could not load pack {idx}: {e}")
                self._packs[idx] = []
        return self._packs[idx]

    def _pack_sizes(self) -> list:
        sizes = []
        for i in range(len(settings.LEVEL_PACKS)):
            pack = self._ensure_pack(i)
            sizes.append(len(pack))
        return sizes

    # ── Level management ──────────────────────────────────────────────────────

    def _load_level(self, pack_idx: int, level_idx: int) -> bool:
        pack = self._ensure_pack(pack_idx)
        if not pack:
            return False
        level_idx = max(0, min(level_idx, len(pack) - 1))
        import copy
        self.level = copy.deepcopy(pack[level_idx])
        self.level.index = level_idx
        self.player = Player(*self.level.player_pos)
        self.history.clear()
        self.moves     = 0
        self.pushes    = 0
        self._start_time = time.time()
        self._elapsed  = 0.0
        self._move_log = []
        self.current_pack    = pack_idx
        self.current_lvl_idx = level_idx
        savegame.set('current_pack',  pack_idx)
        savegame.set('current_level', level_idx)
        return True

    def _restart_level(self) -> None:
        if self._tournoi_mode:
            self._tournoi_attempt += 1
        self._save_incomplete_attempt()
        self._load_level(self.current_pack, self.current_lvl_idx)

    def _next_level(self) -> None:
        if self._tournoi_mode:
            pack     = self._ensure_pack(self._tournoi_pack)
            next_idx = self.current_lvl_idx + 1
            if next_idx < len(pack):
                self._tournoi_attempt = 1
                self._start_transition()
                self._load_level(self._tournoi_pack, next_idx)
                self.state = GameState.PLAYING
            else:
                self._enter_tournoi_end()
            return
        pack = self._ensure_pack(self.current_pack)
        next_idx = self.current_lvl_idx + 1
        if next_idx < len(pack):
            self._start_transition()
            self._load_level(self.current_pack, next_idx)
            self.state = GameState.PLAYING
        else:
            # Pack complete — go to menu
            self._start_transition()
            self.state = GameState.MENU

    # ── Transition helpers ────────────────────────────────────────────────────

    def _start_transition(self, style: str = 'pixelate') -> None:
        self.transition.start(self.logical.copy(), style)

    # ── State transitions ─────────────────────────────────────────────────────

    def _enter_playing(self, pack_idx: int, level_idx: int) -> None:
        if self._load_level(pack_idx, level_idx):
            self._is_replay = False
            self._start_transition('scanwipe')
            self.state = GameState.PLAYING
            audio.play_music('music_game.ogg')

    def _enter_menu(self) -> None:
        if self.state == GameState.PLAYING:
            self._save_incomplete_attempt()
        audio.play_music('music_menu.ogg')
        if not self.student_name:
            self.profile_select_screen.refresh()
            self._start_transition()
            self.state = GameState.PROFILE_SELECT
            return
        self._start_transition()
        self.state = GameState.MENU

    def _enter_level_select(self) -> None:
        if self.state == GameState.PLAYING:
            self._save_incomplete_attempt()
        self.level_select.set_pack(self.current_pack)
        self.level_select.set_pack_sizes(self._pack_sizes())
        self.level_select.student_name = self.student_name
        self._start_transition()
        self.state = GameState.LEVEL_SELECT

    def _enter_replay(self, attempt: dict) -> None:
        pack_idx = next(
            (i for i, p in enumerate(settings.LEVEL_PACKS)
             if p['name'] == attempt.get('pack')), 0)
        self._replay_attempt = attempt
        self._is_replay = True
        if self._load_level(pack_idx, attempt['level_idx']):
            self._replay_ctrl = ReplayController(
                attempt.get('move_log', []),
                settings.REPLAY_DEFAULT_SPEED)
            self._start_transition('scanwipe')
            self.state = GameState.REPLAY
            audio.play_music('music_game.ogg')

    def _exit_replay(self) -> None:
        self._is_replay   = False
        self._replay_ctrl = None
        self._start_transition()
        self.state = GameState.PROF_MENU

    def _enter_tournoi_pack_select(self) -> None:
        self._start_transition()
        self.state = GameState.TOURNOI_PACK_SELECT

    def _enter_tournoi_intro(self, pack_idx: int) -> None:
        pack_name = settings.LEVEL_PACKS[pack_idx]['name']
        self._pending_tournoi_pack = pack_idx
        self.tournoi_intro_screen  = TournoiIntroScreen(pack_name)
        self._start_transition()
        self.state = GameState.TOURNOI_INTRO

    def _enter_tournoi(self, pack_idx: int) -> None:
        self._tournoi_mode       = True
        self._tournoi_pack       = pack_idx
        self._tournoi_attempt    = 1
        self._tournoi_scores     = []
        self._tournoi_session_ts = datetime.now().isoformat(timespec='seconds')
        self._win_tournoi_score  = None
        self._enter_playing(pack_idx, 0)

    def _enter_tournoi_end(self) -> None:
        pack_name = settings.LEVEL_PACKS[self._tournoi_pack]['name']
        total = sum(s['score'] for s in self._tournoi_scores)
        if self.student_name:
            student.save_tournament(self.student_name, pack_name,
                                    self._tournoi_scores, total,
                                    session_ts=self._tournoi_session_ts,
                                    completed=True)
        self.tournoi_end_screen = TournoiEndScreen(
            pack_name, self._tournoi_scores, total)
        self._tournoi_mode = False
        self._start_transition()
        self.state = GameState.TOURNOI_END

    def _enter_entrainement_menu(self) -> None:
        self._start_transition()
        self.state = GameState.ENTRAINEMENT_MENU
        audio.play_music('music_menu.ogg')

    def _handle_entrainement_menu_event(self, event) -> None:
        action = self.entrainement_menu.handle_event(event)
        if action == 'level_select':
            self._enter_level_select()
        elif action == 'back':
            self._enter_menu()

    # ── Student attempt helpers ───────────────────────────────────────────────

    def _save_incomplete_attempt(self) -> None:
        if (self.student_name
                and self.level is not None
                and self.moves > 0
                and not self._is_replay):
            pack_name = settings.LEVEL_PACKS[self.current_pack]['name']
            student.save_attempt(
                self.student_name, pack_name, self.current_lvl_idx,
                completed=False, moves=self.moves, pushes=self.pushes,
                time_sec=self._elapsed, stars=0,
                move_log=self._move_log[:],
                game_type="TRN" if self._tournoi_mode else "ENT")

    # ── Event handling ────────────────────────────────────────────────────────

    def _handle_events(self) -> bool:
        """Returns False if the game should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F4 and (
                        event.mod & pygame.KMOD_ALT):
                    return False

            if self.state == GameState.PROFILE_SELECT:
                if not self._handle_profile_select_event(event):
                    return False

            elif self.state == GameState.MENU:
                if not self._handle_menu_event(event):
                    return False

            elif self.state == GameState.ENTRAINEMENT_MENU:
                self._handle_entrainement_menu_event(event)

            elif self.state == GameState.LEVEL_SELECT:
                self._handle_level_select_event(event)

            elif self.state == GameState.OPTIONS:
                self._handle_options_event(event)

            elif self.state == GameState.PLAYING:
                if not self._handle_play_event(event):
                    return False

            elif self.state == GameState.PAUSED:
                self._handle_pause_event(event)

            elif self.state == GameState.WIN:
                self._handle_win_event(event)

            elif self.state == GameState.PROF_LOGIN:
                self._handle_prof_login_event(event)

            elif self.state == GameState.PROF_MENU:
                self._handle_prof_menu_event(event)

            elif self.state == GameState.REPLAY:
                self._handle_replay_event(event)

            elif self.state == GameState.TOURNOI_PACK_SELECT:
                self._handle_tournoi_pack_select_event(event)

            elif self.state == GameState.TOURNOI_INTRO:
                self._handle_tournoi_intro_event(event)

            elif self.state == GameState.TOURNOI_END:
                self._handle_tournoi_end_event(event)

        return True

    def _handle_profile_select_event(self, event) -> bool:
        result = self.profile_select_screen.handle_event(event)
        if result is None:
            return True
        if result['action'] == 'student':
            self.student_name = result['name']
            self._start_transition()
            self.state = GameState.MENU
        elif result['action'] == 'teacher':
            self.teacher_login.reset()
            self._start_transition()
            self.state = GameState.PROF_LOGIN
        elif result['action'] == 'quit':
            return False
        return True

    def _handle_menu_event(self, event) -> bool:
        action = self.main_menu.handle_event(event)
        if action == 'play':
            self._enter_entrainement_menu()
        elif action == 'tournoi':
            self._enter_tournoi_pack_select()
        elif action == 'quit':
            return False
        elif action == 'profile_select':
            self.profile_select_screen.refresh()
            self._start_transition()
            self.state = GameState.PROFILE_SELECT
            audio.play_music('music_menu.ogg')
        return True

    def _handle_level_select_event(self, event) -> None:
        result = self.level_select.handle_event(event)
        if result is None:
            return
        if isinstance(result, dict):
            if 'action' in result and result['action'] == 'back':
                self._enter_entrainement_menu()
            elif 'pack' in result:
                self._enter_playing(result['pack'], result['level'])

    def _handle_options_event(self, event) -> None:
        action = self.options_screen.handle_event(event)
        if action == 'back':
            # Apply CRT setting
            self.renderer.set_crt(savegame.get('crt_enabled', True))
            # Apply fullscreen
            self._apply_fullscreen()
            savegame.save()
            self._start_transition()
            self.state = GameState.PROF_MENU

    def _apply_fullscreen(self) -> None:
        fs = savegame.get('fullscreen', False)
        flags = pygame.FULLSCREEN if fs else 0
        self.window = pygame.display.set_mode(
            (settings.WINDOW_W, settings.WINDOW_H), flags)

    def _handle_play_event(self, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return True

        key = event.key
        mod = event.mod

        # Movement
        dx, dy = 0, 0
        if key in settings.KEY_UP:    dy = -1
        elif key in settings.KEY_DOWN:  dy =  1
        elif key in settings.KEY_LEFT:  dx = -1
        elif key in settings.KEY_RIGHT: dx =  1

        if dx != 0 or dy != 0:
            self._do_move(dx, dy)
            return True

        # Undo
        if key in settings.KEY_UNDO:
            self._do_undo()
            return True

        # Redo (R without shift)
        if key in settings.KEY_REDO and not (mod & pygame.KMOD_SHIFT):
            self._do_redo()
            return True

        # Restart (Shift+R or F5)
        if (key in settings.KEY_REDO and (mod & pygame.KMOD_SHIFT)) or \
                key in settings.KEY_RESTART:
            self._restart_level()
            return True

        # Pause
        if key in settings.KEY_PAUSE:
            self.pause_screen.tournoi_mode = self._tournoi_mode
            self.pause_screen._selected = min(
                self.pause_screen._selected, len(self.pause_screen._items) - 1
            )
            self.state = GameState.PAUSED
            return True

        return True

    def _handle_pause_event(self, event) -> None:
        action = self.pause_screen.handle_event(event)
        if action == 'resume':
            self.state = GameState.PLAYING
        elif action == 'restart':
            self._restart_level()
            self.state = GameState.PLAYING
        elif action == 'level_select':
            self._enter_level_select()
        elif action == 'main_menu':
            self._enter_menu()

    def _handle_win_event(self, event) -> None:
        action = self.win_screen.handle_event(event)
        if action == 'next_level':
            self._next_level()
        elif action == 'retry':
            if self._tournoi_mode and self._tournoi_scores:
                self._tournoi_scores.pop()  # discard score from this attempt
            self._restart_level()
            self.state = GameState.PLAYING
        elif action == 'level_select':
            self._enter_level_select()

    def _handle_prof_login_event(self, event) -> None:
        action = self.teacher_login.handle_event(event)
        if action == 'login_ok':
            self.teacher_menu.refresh()
            self._start_transition()
            self.state = GameState.PROF_MENU
        elif action == 'back':
            if self.student_name:
                self._enter_menu()
            else:
                self._start_transition()
                self.state = GameState.PROFILE_SELECT

    def _handle_prof_menu_event(self, event) -> None:
        result = self.teacher_menu.handle_event(event)
        if result is None:
            return
        if result.get('action') == 'exit':
            self._enter_menu()
        elif result.get('action') == 'options':
            self._start_transition()
            self.state = GameState.OPTIONS
        elif result.get('action') == 'replay':
            self._enter_replay(result['attempt'])

    def _replay_seek(self, target_pos: int) -> None:
        if self._replay_ctrl is None or not self._replay_attempt:
            return
        pack_idx = next(
            (i for i, p in enumerate(settings.LEVEL_PACKS)
             if p['name'] == self._replay_attempt.get('pack')), 0)
        self._load_level(pack_idx, self._replay_attempt['level_idx'])
        target_pos = max(0, min(target_pos, len(self._replay_ctrl._log)))
        for action in self._replay_ctrl._log[:target_pos]:
            if action == 'U':   self._do_move(0, -1)
            elif action == 'D': self._do_move(0, 1)
            elif action == 'L': self._do_move(-1, 0)
            elif action == 'R': self._do_move(1, 0)
            elif action == 'Z': self._do_undo()
            elif action == 'Y': self._do_redo()
        self._replay_ctrl._pos = target_pos
        self._replay_ctrl._frames_until_next = self._replay_ctrl._speed

    def _handle_replay_event(self, event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_SPACE:
            if self._replay_ctrl:
                self._replay_ctrl.toggle_pause()
        elif event.key in settings.KEY_UP:
            if self._replay_ctrl:
                self._replay_ctrl.set_speed(
                    max(1, self._replay_ctrl._speed - 2))
        elif event.key in settings.KEY_DOWN:
            if self._replay_ctrl:
                self._replay_ctrl.set_speed(
                    self._replay_ctrl._speed + 2)
        elif event.key in settings.KEY_LEFT:
            if self._replay_ctrl and self._replay_ctrl.paused and self._replay_ctrl._pos > 0:
                self._replay_seek(self._replay_ctrl._pos - 1)
        elif event.key in settings.KEY_RIGHT:
            if self._replay_ctrl and self._replay_ctrl.paused:
                action = self._replay_ctrl.step_forward()
                if action == 'U':   self._do_move(0, -1)
                elif action == 'D': self._do_move(0, 1)
                elif action == 'L': self._do_move(-1, 0)
                elif action == 'R': self._do_move(1, 0)
                elif action == 'Z': self._do_undo()
                elif action == 'Y': self._do_redo()
        elif event.key == pygame.K_r:
            if self._replay_ctrl:
                self._replay_seek(0)
                self._replay_ctrl._paused = False
        elif event.key in settings.KEY_PAUSE:
            self._exit_replay()

    def _handle_tournoi_pack_select_event(self, event) -> None:
        result = self.tournoi_pack_select.handle_event(event)
        if result is None:
            return
        if result == 'back':
            self._enter_menu()
        elif isinstance(result, dict) and 'pack' in result:
            self._enter_tournoi_intro(result['pack'])

    def _handle_tournoi_intro_event(self, event) -> None:
        if self.tournoi_intro_screen is None:
            return
        action = self.tournoi_intro_screen.handle_event(event)
        if action == 'start':
            self._enter_tournoi(self._pending_tournoi_pack)
        elif action == 'back':
            self._enter_tournoi_pack_select()

    def _handle_tournoi_end_event(self, event) -> None:
        if self.tournoi_end_screen is None:
            return
        result = self.tournoi_end_screen.handle_event(event)
        if result == 'back':
            self._enter_menu()

    # ── Gameplay actions ──────────────────────────────────────────────────────

    def _do_move(self, dx: int, dy: int) -> None:
        if self.level is None or self.player is None:
            return
        result = self.level.try_move(dx, dy)
        if result.moved:
            self.moves += 1
            if result.pushed:
                self.pushes += 1
                audio.play_sfx('push.wav')
                # Box bounce effect
                if result.box_to:
                    self.renderer.trigger_box_bounce(*result.box_to)
            else:
                audio.play_sfx('move.wav')
            self.history.push(result)
            self.player.sync(*self.level.player_pos, True, result.pushed, dx, dy)

            # Record move in log (skip during replay)
            if not self._is_replay:
                code = ('R' if dx > 0 else 'L' if dx < 0
                        else 'D' if dy > 0 else 'U')
                self._move_log.append(code)

            if result.completed:
                self._on_level_complete()
        else:
            # Invalid move — screen shake
            self.player.trigger_invalid(dx, dy)

    def _do_undo(self) -> None:
        if self.level is None or self.player is None:
            return
        result = self.history.undo()
        if result:
            self.level.apply_undo(result)
            self.player.sync(*self.level.player_pos, False, False)
            self.moves  = max(0, self.moves  - 1)
            if result.pushed:
                self.pushes = max(0, self.pushes - 1)
            audio.play_sfx('undo.wav')
            if not self._is_replay:
                self._move_log.append('Z')

    def _do_redo(self) -> None:
        if self.level is None or self.player is None:
            return
        result = self.history.redo()
        if result:
            self.level.apply_redo(result)
            self.player.sync(*self.level.player_pos, False, False)
            self.moves  += 1
            if result.pushed:
                self.pushes += 1
            if not self._is_replay:
                self._move_log.append('Y')

    def _on_level_complete(self) -> None:
        if self.level is None:
            return
        if self._is_replay:
            return  # don't process win during replay

        elapsed   = time.time() - self._start_time
        pack_name = settings.LEVEL_PACKS[self.current_pack]['name']
        stars     = savegame.compute_stars(self.moves, self.level.optimal_moves)
        is_best   = student.record_score(
            self.student_name, pack_name, self.current_lvl_idx,
            self.moves, self.pushes, elapsed, stars)
        student.unlock_level(self.student_name, pack_name, self.current_lvl_idx)

        # Compute tournament score first (needed for save_attempt tag)
        undos = self._move_log.count('Z')
        if self._tournoi_mode:
            ts = savegame.compute_tournoi_level_score(
                self.moves, self._tournoi_attempt, elapsed,
                self.level.optimal_moves, undos)
        else:
            ts = 0

        # Save completed attempt for the current student
        if self.student_name:
            student.save_attempt(
                self.student_name, pack_name, self.current_lvl_idx,
                completed=True, moves=self.moves, pushes=self.pushes,
                time_sec=elapsed, stars=stars,
                move_log=self._move_log[:],
                game_type="TRN" if self._tournoi_mode else "ENT",
                score=ts, undos=undos)

        audio.play_sfx('solve.wav')

        # Particle burst at each box (they're all on targets)
        ox, oy = self.renderer.level_offset(self.level)
        for bx, by in self.level.boxes:
            self.renderer.spawn_particles(bx, by, ox, oy)

        self._win_is_best = is_best
        self._win_stars   = stars

        if self._tournoi_mode:
            self._tournoi_scores.append({
                'level_idx': self.current_lvl_idx,
                'score':     ts,
                'moves':     self.moves,
                'attempts':  self._tournoi_attempt,
                'time':      round(elapsed, 1),
                'undos':     undos,
            })
            # Save progress after each level so partial runs are persisted
            if self.student_name:
                partial_total = sum(s['score'] for s in self._tournoi_scores)
                student.save_tournament(
                    self.student_name, pack_name,
                    self._tournoi_scores, partial_total,
                    session_ts=self._tournoi_session_ts,
                    completed=False)
            self._win_tournoi_score = ts
            self.win_screen.reset(tournoi_score=ts)
        else:
            self._win_tournoi_score = None
            self.win_screen.reset()
        self.state = GameState.WIN

    # ── Update ────────────────────────────────────────────────────────────────

    def _update(self) -> None:
        if self.state == GameState.PLAYING:
            if self.player:
                self.player.update()
            self._elapsed = time.time() - self._start_time

        elif self.state == GameState.REPLAY:
            if self.player:
                self.player.update()
            if self._replay_ctrl and not self._replay_ctrl.is_done:
                action = self._replay_ctrl.tick()
                if action == 'U':
                    self._do_move(0, -1)
                elif action == 'D':
                    self._do_move(0, 1)
                elif action == 'L':
                    self._do_move(-1, 0)
                elif action == 'R':
                    self._do_move(1, 0)
                elif action == 'Z':
                    self._do_undo()
                elif action == 'Y':
                    self._do_redo()

        self.transition.update()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        self.logical.fill(settings.COLOR_BG)

        # Draw game tiles/sprites on logical surface
        if self.state in (GameState.PLAYING, GameState.PAUSED,
                          GameState.WIN, GameState.REPLAY):
            if self.level and self.player:
                self.renderer.draw_level(self.level, self.player)

        # Transition overlay on logical surface
        if self.transition.active:
            self.transition.draw(self.logical)

        # Scale logical → window
        scaled = pygame.transform.scale(
            self.logical, (settings.WINDOW_W, settings.WINDOW_H))
        self.window.blit(scaled, (0, 0))

        # Draw all UI text on the window surface (post-scale) for crisp rendering
        scale = settings.SCALE

        if self.state == GameState.PROFILE_SELECT:
            self.profile_select_screen.draw(self.window, self.font_md, scale)
            self.renderer.apply_crt_rects(self.window,
                self.profile_select_screen.board_rects)

        elif self.state == GameState.MENU:
            self.main_menu.draw(self.window, self.font_md, scale,
                                student_name=self.student_name)

        elif self.state == GameState.ENTRAINEMENT_MENU:
            self.entrainement_menu.draw(self.window, self.font_md, scale,
                                        student_name=self.student_name)

        elif self.state == GameState.LEVEL_SELECT:
            self.level_select.draw(self.window, self.font_sm, self.font_md, scale)

        elif self.state == GameState.OPTIONS:
            self.options_screen.draw(self.window, self.font_sm, scale)

        elif self.state == GameState.PROF_LOGIN:
            self.teacher_login.draw(self.window, self.font_md, scale)

        elif self.state == GameState.PROF_MENU:
            self.teacher_menu.draw(self.window, self.font_md, scale)

        elif self.state == GameState.TOURNOI_PACK_SELECT:
            self.tournoi_pack_select.draw(self.window, self.font_md, scale)

        elif self.state == GameState.TOURNOI_INTRO:
            if self.tournoi_intro_screen:
                self.tournoi_intro_screen.draw(self.window, self.font_md, scale)

        elif self.state == GameState.TOURNOI_END:
            if self.tournoi_end_screen:
                self.tournoi_end_screen.draw(self.window, self.font_md, scale)

        elif self.state in (GameState.PLAYING, GameState.PAUSED,
                            GameState.WIN, GameState.REPLAY):
            if self.level and self.player:
                pack_name = settings.LEVEL_PACKS[self.current_pack]['name']
                pack = self._ensure_pack(self.current_pack)
                hud.draw(
                    self.window, self.font_sm,
                    self.level.title, pack_name,
                    self.current_lvl_idx, len(pack),
                    self.moves, self.pushes, self._elapsed,
                    self.history.can_undo(),
                    scale,
                    student_name=self.student_name,
                    tournoi_attempt=(self._tournoi_attempt
                                     if self._tournoi_mode else 0),
                )

            if self.state == GameState.PAUSED:
                self.pause_screen.draw(self.window, self.font_md, scale)
            elif self.state == GameState.WIN:
                self.win_screen.draw(
                    self.window, self.font_sm,
                    self.level.title if self.level else "",
                    self.moves, self.pushes, self._elapsed,
                    self._win_stars, self._win_is_best,
                    scale,
                    tournoi_score=self._win_tournoi_score,
                )
            elif self.state == GameState.REPLAY:
                self._draw_replay_hud()

        pygame.display.flip()

    def _draw_replay_hud(self) -> None:
        if self._replay_ctrl is None:
            return
        W, H   = self.window.get_size()
        margin = 20

        # REPLAY label at top-centre
        s = self.font_sm.render("[ REPLAY ]", False, settings.MAGENTA)
        self.window.blit(s, (W // 2 - s.get_width() // 2, 8))

        # Bottom strip
        strip_h = 36
        strip_y = H - strip_h
        bg = pygame.Surface((W, strip_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.window.blit(bg, (0, strip_y))

        # Progress bar
        bar_w = W - 2 * margin
        bar_h = 8
        bar_y = strip_y + 6
        pygame.draw.rect(self.window, settings.DARK_GRAY,
                         (margin, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * self._replay_ctrl.progress)
        if fill_w > 0:
            pygame.draw.rect(self.window, settings.CYAN,
                             (margin, bar_y, fill_w, bar_h))
        pygame.draw.rect(self.window, settings.LIGHT_GRAY,
                         (margin, bar_y, bar_w, bar_h), 1)

        # PAUSED indicator (left side)
        if self._replay_ctrl.paused:
            s = self.font_sm.render("■ PAUSE", False, settings.YELLOW)
            self.window.blit(s, (margin, strip_y + 18))

        # Speed indicator (right side)
        spd = self._replay_ctrl._speed
        s = self.font_sm.render(f"{spd}f/coup", False, settings.LIGHT_GRAY)
        self.window.blit(s, (W - s.get_width() - margin, strip_y + 18))

        # Controls hint (centre)
        if self._replay_ctrl.paused:
            hint = "FL G/D:PAS A PAS  R:RESTART  FL H/B:VITESSE  ÉCHAP:QUITTER"
        else:
            hint = "ESPACE:PAUSE  FL H/B:VITESSE  ÉCHAP:QUITTER"
        s = self.font_sm.render(hint, False, settings.DARK_GRAY)
        self.window.blit(s, (W // 2 - s.get_width() // 2, strip_y + 18))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        running = True
        while running:
            running = self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(settings.FPS)

        savegame.save()
        pygame.quit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    game = Game()
    game.run()
