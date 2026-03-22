# settings.py — All constants for the Sokoban game

import os
import pygame
import sys

# ── Display ───────────────────────────────────────────────────────────────────
TILE_SIZE    = 16        # logical pixels per tile
SCALE        = 3         # upscale factor: 16px → 48px on screen
LOGICAL_W    = 320       # logical canvas width
LOGICAL_H    = 240       # logical canvas height
WINDOW_W     = LOGICAL_W * SCALE
WINDOW_H     = LOGICAL_H * SCALE
FPS          = 60
WINDOW_TITLE = "SOKOBAN"

# ── EGA 16-Color Palette ─────────────────────────────────────────────────────
BLACK       = (  0,   0,   0)
DARK_BLUE   = (  0,   0, 170)
DARK_GREEN  = (  0, 170,   0)
DARK_CYAN   = (  0, 170, 170)
DARK_RED    = (170,   0,   0)
DARK_MAGENTA= (170,   0, 170)
BROWN       = (170,  85,   0)
LIGHT_GRAY  = (170, 170, 170)
DARK_GRAY   = ( 85,  85,  85)
BLUE        = ( 85,  85, 255)
GREEN       = ( 85, 255,  85)
CYAN        = ( 85, 255, 255)
RED         = (255,  85,  85)
MAGENTA     = (255,  85, 255)
YELLOW      = (255, 255,  85)
WHITE       = (255, 255, 255)

EGA_PALETTE = [
    BLACK, DARK_BLUE, DARK_GREEN, DARK_CYAN,
    DARK_RED, DARK_MAGENTA, BROWN, LIGHT_GRAY,
    DARK_GRAY, BLUE, GREEN, CYAN, RED, MAGENTA, YELLOW, WHITE,
]

# ── Game Colors (semantic) ────────────────────────────────────────────────────
COLOR_BG          = BLACK
COLOR_FLOOR       = DARK_GRAY
COLOR_WALL        = LIGHT_GRAY
COLOR_TARGET      = DARK_CYAN
COLOR_BOX         = BROWN
COLOR_BOX_DONE    = GREEN
COLOR_PLAYER      = YELLOW
COLOR_DARK_FLOOR  = (30, 30, 30)
COLOR_HUD_BG      = (0, 0, 0, 180)
COLOR_HUD_TEXT    = WHITE
COLOR_HIGHLIGHT   = CYAN
COLOR_MENU_BG     = BLACK
COLOR_MENU_TITLE  = YELLOW
COLOR_MENU_ITEM   = WHITE
COLOR_MENU_SELECT = CYAN
COLOR_WIN_BG      = DARK_BLUE
COLOR_STAR        = YELLOW
COLOR_STAR_EMPTY  = DARK_GRAY

# ── Keybindings ───────────────────────────────────────────────────────────────

KEY_UP      = [pygame.K_UP,    pygame.K_z]
KEY_DOWN    = [pygame.K_DOWN,  pygame.K_s]
KEY_LEFT    = [pygame.K_LEFT,  pygame.K_q]
KEY_RIGHT   = [pygame.K_RIGHT, pygame.K_d]
KEY_UNDO    = [pygame.K_u]
KEY_REDO    = [pygame.K_r]          # R = redo (Shift+R = restart handled separately)
KEY_RESTART = [pygame.K_F5]
KEY_PAUSE   = [pygame.K_ESCAPE]
KEY_CONFIRM = [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE]
KEY_NEXT    = [pygame.K_n]
KEY_PREV    = [pygame.K_p]

# ── XSB Tile Characters ───────────────────────────────────────────────────────
XSB_FLOOR          = ' '
XSB_WALL           = '#'
XSB_PLAYER         = '@'
XSB_PLAYER_TARGET  = '+'
XSB_BOX            = '$'
XSB_BOX_TARGET     = '*'
XSB_TARGET         = '.'

# ── Animation ─────────────────────────────────────────────────────────────────
WALK_FRAME_DURATION  = 8    # frames per walk animation step
PUSH_FRAME_DURATION  = 6
BOX_BOUNCE_FRAMES    = 10   # frames for box scale-bounce
SHAKE_FRAMES         = 8    # invalid-move screen shake duration
SHAKE_AMPLITUDE      = 2    # pixels (logical)
PARTICLE_COUNT       = 20
PARTICLE_LIFETIME    = 45   # frames

# ── Sprites ───────────────────────────────────────────────────────────────────
USE_PROCEDURAL_SPRITES = True   # flip to False when PNG assets are ready
SPRITE_TILE_SIZE = 16           # sprite sheet cell size

# ── Audio ─────────────────────────────────────────────────────────────────────
DEFAULT_SFX_VOLUME   = 0.7
DEFAULT_MUSIC_VOLUME = 0.4

# ── History ──────────────────────────────────────────────────────────────────
MAX_HISTORY = 200

# ── Scoring (stars) ──────────────────────────────────────────────────────────
STAR_3_MULTIPLIER = 1.0    # ≤ optimal moves → 3 stars
STAR_2_MULTIPLIER = 1.5    # ≤ 1.5× optimal  → 2 stars
STAR_1_MULTIPLIER = 2.5    # ≤ 2.5× optimal  → 1 star

# ── Tournoi Scoring ───────────────────────────────────────────────────────────
TOURNOI_MOVES_MAX    = 1000
TOURNOI_ATTEMPTS_MAX = 500
TOURNOI_ATTEMPTS_PEN = 100   # deducted per extra attempt
TOURNOI_TIME_MAX     = 500   # deducted 1 pt per second
TOURNOI_UNDO_PEN     = 1     # deducted per undo move

# ── CRT Effect ────────────────────────────────────────────────────────────────
CRT_SCANLINE_ALPHA  = 60   # 0-255 darkness of scanlines
CRT_VIGNETTE_ALPHA  = 120  # corner vignette strength

# ── Save file ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH   = os.path.join(_BASE, 'save.json')
ASSETS_DIR  = os.path.join(_BASE, 'assets')
LEVELS_DIR  = os.path.join(_BASE, 'levels')

# ── Level packs ──────────────────────────────────────────────────────────────
LEVEL_PACKS = [
    {"name": "Training",  "file": "training.xsb",  "always_unlocked": True},
    {"name": "Easy",      "file": "easy.xsb"},
    {"name": "Original",  "file": "original.xsb"},
    {"name": "Microban",  "file": "microban.xsb"},
    {"name": "Sasquatch", "file": "sasquatch.xsb"},
    {"name": "Saint-Luc", "file": "saintluc.xsb",  "always_unlocked": True},
]

# ── HUD ──────────────────────────────────────────────────────────────────────
HUD_HEIGHT = 20    # pixels at bottom reserved for HUD (logical coords)

# ── Student / Teacher ────────────────────────────────────────────────────────
# PIN stored as base64 to avoid plaintext in source; not cryptographically secure
# base64.b64encode(b"1234").decode() == "MTIzNA=="
PROF_PIN_B64 = "MTk4NQ=="   # teacher changes this value (base64 of the PIN)
STUDENT_HMAC_KEY_B64 = "DdYESWa5nfuhIfmAZVkNW05PyidLL19CoXLhrj5wrE4="  # integrity key (do not change)
STUDENTS_DIR = os.path.join(_BASE, "students")
REPLAY_DEFAULT_SPEED = 15   # frames between replay moves (lower = faster)
