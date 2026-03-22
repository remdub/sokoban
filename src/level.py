# src/level.py — XSB parser, board state, move validation

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import settings

# Direction vectors
DIR_UP    = ( 0, -1)
DIR_DOWN  = ( 0,  1)
DIR_LEFT  = (-1,  0)
DIR_RIGHT = ( 1,  0)
DIRECTIONS = [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]

# Tile types (internal)
T_VOID   = 0
T_FLOOR  = 1
T_WALL   = 2
T_TARGET = 3

XSB_DECODE = {
    ' ': (T_FLOOR,  False, False),
    '#': (T_WALL,   False, False),
    '@': (T_FLOOR,  True,  False),   # player
    '+': (T_TARGET, True,  False),   # player on target
    '$': (T_FLOOR,  False, True),    # box
    '*': (T_TARGET, False, True),    # box on target
    '.': (T_TARGET, False, False),
    '-': (T_FLOOR,  False, False),   # alternate floor
    '_': (T_FLOOR,  False, False),   # alternate floor
}


@dataclass
class MoveResult:
    """Result of a move operation — used by history for undo."""
    moved: bool = False
    pushed: bool = False
    player_from: Tuple[int, int] = (0, 0)
    player_to:   Tuple[int, int] = (0, 0)
    box_from:    Optional[Tuple[int, int]] = None
    box_to:      Optional[Tuple[int, int]] = None
    completed:   bool = False


@dataclass
class Level:
    title: str = ""
    author: str = ""
    width: int = 0
    height: int = 0
    tiles: List[List[int]] = field(default_factory=list)
    # Mutable state (current play state)
    player_pos: Tuple[int, int] = (0, 0)
    boxes: List[Tuple[int, int]] = field(default_factory=list)
    targets: List[Tuple[int, int]] = field(default_factory=list)
    # Optimal move count for star rating (0 = unknown)
    optimal_moves: int = 0
    # Index within its pack
    index: int = 0
    pack_name: str = ""

    # ── Computed helpers ─────────────────────────────────────────────────────

    def tile_at(self, x: int, y: int) -> int:
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.tiles[y][x]
        return T_VOID

    def is_walkable(self, x: int, y: int) -> bool:
        return self.tile_at(x, y) in (T_FLOOR, T_TARGET)

    def has_box(self, x: int, y: int) -> bool:
        return (x, y) in self.boxes

    def is_complete(self) -> bool:
        return all(b in self.targets for b in self.boxes)

    # ── Movement ─────────────────────────────────────────────────────────────

    def try_move(self, dx: int, dy: int) -> MoveResult:
        px, py = self.player_pos
        nx, ny = px + dx, py + dy
        result = MoveResult(player_from=(px, py), player_to=(px, py))

        if not self.is_walkable(nx, ny):
            return result  # wall or void

        if self.has_box(nx, ny):
            bx, by = nx + dx, ny + dy
            if not self.is_walkable(bx, by) or self.has_box(bx, by):
                return result  # can't push box
            # Push box
            self.boxes[self.boxes.index((nx, ny))] = (bx, by)
            result.pushed   = True
            result.box_from = (nx, ny)
            result.box_to   = (bx, by)

        self.player_pos = (nx, ny)
        result.moved      = True
        result.player_to  = (nx, ny)
        result.completed  = self.is_complete()
        return result

    def apply_undo(self, result: MoveResult) -> None:
        """Reverse a MoveResult."""
        if not result.moved:
            return
        self.player_pos = result.player_from
        if result.pushed and result.box_to and result.box_from:
            idx = self.boxes.index(result.box_to)
            self.boxes[idx] = result.box_from

    def apply_redo(self, result: MoveResult) -> None:
        """Re-apply a MoveResult."""
        if not result.moved:
            return
        self.player_pos = result.player_to
        if result.pushed and result.box_from and result.box_to:
            idx = self.boxes.index(result.box_from)
            self.boxes[idx] = result.box_to

    def clone_state(self) -> dict:
        return {
            'player_pos': self.player_pos,
            'boxes': list(self.boxes),
        }

    def restore_state(self, state: dict) -> None:
        self.player_pos = state['player_pos']
        self.boxes = list(state['boxes'])


# ── XSB File Parser ───────────────────────────────────────────────────────────

def _parse_block(lines: List[str], index: int, pack_name: str) -> Level:
    """Parse a single level block (list of XSB lines) into a Level."""
    level = Level(index=index, pack_name=pack_name)

    # Extract metadata comments
    board_lines = []
    for line in lines:
        stripped = line.rstrip('\n\r')
        if stripped.startswith(';'):
            meta = stripped[1:].strip()
            if meta.lower().startswith('title:'):
                level.title = meta[6:].strip()
            elif meta.lower().startswith('author:'):
                level.author = meta[7:].strip()
            elif meta.lower().startswith('optimal:'):
                try:
                    level.optimal_moves = int(meta[8:].strip())
                except ValueError:
                    pass
            # Keep comment lines out of board
        else:
            board_lines.append(stripped)

    if not level.title:
        level.title = f"Level {index + 1}"

    if not board_lines:
        raise ValueError("Empty level block")

    level.height = len(board_lines)
    level.width  = max(len(l) for l in board_lines)

    for row_idx, raw in enumerate(board_lines):
        row_tiles = []
        for col_idx in range(level.width):
            ch = raw[col_idx] if col_idx < len(raw) else ' '
            tile_type, is_player, is_box = XSB_DECODE.get(ch, (T_FLOOR, False, False))
            row_tiles.append(tile_type)
            if tile_type == T_TARGET:
                level.targets.append((col_idx, row_idx))
            if is_player:
                level.player_pos = (col_idx, row_idx)
            if is_box:
                level.boxes.append((col_idx, row_idx))
        level.tiles.append(row_tiles)

    return level


def load_levels(filepath: str, pack_name: str = "") -> List[Level]:
    """Load all levels from an XSB file."""
    if not pack_name:
        pack_name = os.path.splitext(os.path.basename(filepath))[0].title()

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.readlines()
    except OSError as e:
        raise OSError(f"Cannot open level file '{filepath}': {e}")

    levels = []
    current_block: List[str] = []

    def flush():
        # Strip trailing empty lines
        block = current_block[:]
        while block and not block[-1].strip():
            block.pop()
        if block:
            # Check if block has any board content (not just comments)
            has_board = any(
                not l.strip().startswith(';') and l.strip()
                for l in block
            )
            if has_board:
                try:
                    lv = _parse_block(block, len(levels), pack_name)
                    levels.append(lv)
                except Exception:
                    pass  # skip malformed blocks

    for line in raw:
        stripped = line.rstrip('\n\r')
        if stripped == '' and current_block:
            flush()
            current_block = []
        else:
            current_block.append(line)

    if current_block:
        flush()

    return levels


def load_pack(pack_info: dict) -> List[Level]:
    """Load a level pack from settings.LEVEL_PACKS entry."""
    filepath = os.path.join(settings.LEVELS_DIR, pack_info['file'])
    return load_levels(filepath, pack_info['name'])
