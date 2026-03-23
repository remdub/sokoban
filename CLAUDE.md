# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

The game targets **Windows 7 compatibility** (Python 3.8, pygame-ce 2.5.2). uv/uvx is not used as it is not Windows 7 compatible.

One-time setup (create a Python 3.8 venv in `bin/`):
```bash
python3.8 -m venv bin
bin/pip install -r requirements.txt
```

Run:
```bash
bin/python main.py
```

## Building for Windows (from Linux/Ubuntu)

The build script `build/build_windows.sh` cross-compiles a standalone Windows executable using Wine + PyInstaller. No Python is required on the target machine.

**Prerequisites:**
- `wine` (`sudo apt install wine`)
- `python-3.8.20.exe` — Windows Python 3.8 installer, downloaded into the repo root (or pass the path as argument)

**Build:**
```bash
bash build/build_windows.sh
# or: bash build/build_windows.sh /path/to/python-3.8.20.exe
```

The script installs Python 3.8 under Wine, then installs `pygame-ce==2.1.4` and `pyinstaller==5.13.2`, and runs PyInstaller with `build/sokoban.spec`.

**Output:** `dist_win/sokoban/` — a self-contained folder (one-dir PyInstaller build bundling `assets/` and `levels/`).

**Distribution:** copy the entire `dist_win/sokoban/` folder to the target Windows PC and launch `sokoban.exe`. The `students/` subfolder and `save.json` are created at runtime next to the exe, so the folder must be writable.

## Architecture

### Display model
Logical canvas is **320×240 px**, scaled ×3 to a 960×720 window. All game drawing targets the logical surface; UI text is drawn post-scale for sharpness. CRT scanline+vignette overlay is applied last.

### State machine (`main.py` — `Game` class)
The game is a single `Game` object with a `GameState` enum. Key states:

```
PROFILE_SELECT → ENTRAINEMENT_MENU → LEVEL_SELECT → PLAYING → WIN
                        ↓                                ↑
                   PROF_LOGIN → PROF_MENU            PAUSED
TOURNOI_PACK_SELECT → TOURNOI_INTRO → PLAYING (tournoi) → TOURNOI_END
REPLAY  (teacher watching a student attempt)
OPTIONS (from MENU)
```

`_handle_events`, `_update`, and `_draw` are the three methods called each frame.

### Key modules (`src/`)

| Module | Responsibility |
|---|---|
| `level.py` | XSB parser, grid state, `try_move()` → `MoveResult` |
| `player.py` | Player grid position, walk/push animation, screen-shake |
| `renderer.py` | All drawing: procedural sprites, particles, CRT effect |
| `menu.py` | All UI screens (main menu, level select, win, options, …) |
| `hud.py` | In-game overlay (moves, pushes, time, student name) |
| `history.py` | Undo/redo stack (`MoveResult` objects, max 200) |
| `audio.py` | SFX + BGM, volume saved in `save.json`; silently no-ops if mixer unavailable |
| `savegame.py` | JSON persistence to `save.json` (level progress, high scores) |
| `student.py` | Per-student attempt logging to `students/<name>.json` |
| `teacher_menu.py` | PIN-protected teacher panel: student submenu → replay attempts or tournament stats |
| `replay.py` | Playback of serialised move logs (U/D/L/R/Z/Y codes) |
| `transition.py` | Pixelate/scanwipe effects between states |

### Teacher panel navigation (`src/teacher_menu.py`)
Internal state machine with modes:
```
home → list → student_submenu → detail (replay attempt list)
                              → tournoi_list → tournoi_detail
home → classe_pack → classe_stats
```
From the home screen:
- **GESTION DES ÉLÈVES** → student list → per-student submenu with two choices: "REPLAY DES PARTIES" (attempt history with replay) and "STATS DES TOURNOIS" (per-student tournament history with per-level breakdown).
- **STATS CLASSE TOURNOI** → pack picker → class stats screen with two toggled views (LEFT/RIGHT): student leaderboard ranked by best score, and per-level averages across the class.

### Move serialisation
Every move is appended to `self._move_log` as a single character (`U`/`D`/`L`/`R`); undo/redo are logged as `Z`/`Y`. Saved with student attempts. `replay.py` drives playback by replaying these characters through the same `_do_move` path.

### Settings (`settings.py`)
All game constants live here:
- **Keybindings**: Arrow keys + ZQSD (French AZERTY) for movement; `U`=undo, `R`=redo, `Shift+R`/`F5`=restart
- **Tile chars**: `@` player, `+` player-on-target, `#` wall, `$` box, `*` box-on-target, `.` target
- **Animation durations** (frames @60fps): walk=8, push=6, box bounce=10, shake=8
- **Teacher PIN**: Base64-encoded in `PROF_PIN_B64` (not cryptographic, just obfuscated)

### Scoring
Star ratings (`savegame.compute_stars`):
- 3 stars: moves ≤ optimal × 1.0
- 2 stars: moves ≤ optimal × 1.5
- 1 star: moves ≤ optimal × 2.5

Tournament scoring (`savegame.compute_tournoi_level_score`, max 2000 pts):
- **Moves** (1000 pts): `optimal/actual × 1000`
- **Attempts** (500 pts): `500 − 100×(attempts−1)`, floored at 0
- **Time** (500 pts): `500 − elapsed_seconds`, floored at 0
- **Undo penalty**: −1 pt per undo (Z code in move_log); total floored at 0

### Save data
- `save.json` — game progress, unlock state, high scores, volume. Keys: `version`, `sfx_volume`, `music_volume`, `crt_enabled`, `fullscreen`, `current_pack`, `current_level`.
- `students/<name>.json` — per-student attempt records. Per-attempt fields: `pack`, `level_idx`, `completed`, `moves`, `pushes`, `time`, `stars`, `move_log`, `game_type` (`"ENT"`/`"TRN"`), `score`. Unlock progress stored per-pack under `packs.<pack_name>.unlocked`.

### Level packs
XSB files in `levels/` (`training`, `easy`, `original`, `microban`, `sasquatch`, `saintluc`). Loaded lazily on first access and deep-copied per play session. Optimal move counts stored as `;optimal:N` comments in XSB files; used for star ratings and tournament scoring.
