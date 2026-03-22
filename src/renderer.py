# src/renderer.py — All drawing: tiles, sprites, CRT overlay, vignette, particles

from __future__ import annotations
import math
import random
from typing import List, Tuple, Optional
import pygame
import settings
from src.level import Level, T_FLOOR, T_WALL, T_TARGET, T_VOID
from src.player import Player, FACE_RIGHT, FACE_LEFT, FACE_DOWN, FACE_UP


# ── Particle System ───────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x: float, y: float):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.5, 2.5)
        self.x   = x
        self.y   = y
        self.vx  = math.cos(angle) * speed
        self.vy  = math.sin(angle) * speed
        self.life = settings.PARTICLE_LIFETIME
        self.max_life = settings.PARTICLE_LIFETIME
        self.color = random.choice([
            settings.YELLOW, settings.CYAN, settings.GREEN,
            settings.WHITE, settings.MAGENTA,
        ])
        self.size = random.randint(1, 2)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.05   # gravity
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        alpha_ratio = self.life / self.max_life
        r, g, b = self.color
        color = (
            int(r * alpha_ratio),
            int(g * alpha_ratio),
            int(b * alpha_ratio),
        )
        pygame.draw.rect(surface, color,
                         (int(self.x), int(self.y), self.size, self.size))


# ── Renderer ──────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, logical_surface: pygame.Surface):
        self.surf = logical_surface
        self.w    = logical_surface.get_width()
        self.h    = logical_surface.get_height()

        self._crt_overlay:   Optional[pygame.Surface] = None
        self._vignette:      Optional[pygame.Surface] = None
        self._crt_enabled    = True

        self._particles:     List[Particle] = []
        self._box_bounces:   dict = {}   # (x,y) → remaining frames

        self._build_crt_overlay()
        self._build_vignette()

    # ── CRT surfaces (built once at startup) ─────────────────────────────────

    def _build_crt_overlay(self) -> None:
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for y in range(0, self.h, 2):
            pygame.draw.line(surf,
                             (0, 0, 0, settings.CRT_SCANLINE_ALPHA),
                             (0, y), (self.w, y))
        self._crt_overlay = surf

    def _build_vignette(self) -> None:
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        cx, cy = self.w / 2, self.h / 2
        max_r  = math.sqrt(cx * cx + cy * cy)
        for y in range(self.h):
            for x in range(self.w):
                dx, dy = x - cx, y - cy
                r = math.sqrt(dx * dx + dy * dy)
                ratio = r / max_r
                if ratio > 0.6:
                    alpha = int(settings.CRT_VIGNETTE_ALPHA * ((ratio - 0.6) / 0.4) ** 2)
                    surf.set_at((x, y), (0, 0, 0, min(alpha, 255)))
        self._vignette = surf

    # ── Tile / sprite drawing ─────────────────────────────────────────────────

    def _tile_rect(self, gx: int, gy: int,
                   offset_x: int = 0, offset_y: int = 0) -> pygame.Rect:
        ts = settings.TILE_SIZE
        return pygame.Rect(
            offset_x + gx * ts,
            offset_y + gy * ts,
            ts, ts,
        )

    def _draw_tile(self, gx: int, gy: int, tile: int,
                   offset_x: int, offset_y: int) -> None:
        rect = self._tile_rect(gx, gy, offset_x, offset_y)
        ts   = settings.TILE_SIZE

        if tile == T_VOID:
            return
        if tile == T_WALL:
            pygame.draw.rect(self.surf, settings.COLOR_WALL, rect)
            # Simple bevel: bright top/left, dark bottom/right
            pygame.draw.line(self.surf, settings.WHITE,
                             rect.topleft, rect.topright)
            pygame.draw.line(self.surf, settings.WHITE,
                             rect.topleft, rect.bottomleft)
            pygame.draw.line(self.surf, settings.DARK_GRAY,
                             rect.bottomleft, rect.bottomright)
            pygame.draw.line(self.surf, settings.DARK_GRAY,
                             rect.topright, rect.bottomright)
        elif tile == T_FLOOR:
            pygame.draw.rect(self.surf, settings.COLOR_FLOOR, rect)
            # Subtle grid dot
            cx, cy = rect.x + ts // 2, rect.y + ts // 2
            pygame.draw.rect(self.surf, settings.COLOR_DARK_FLOOR,
                             (cx - 1, cy - 1, 2, 2))
        elif tile == T_TARGET:
            pygame.draw.rect(self.surf, settings.COLOR_FLOOR, rect)
            # Draw a cross / diamond for target
            m = 3
            pygame.draw.rect(self.surf, settings.COLOR_TARGET,
                             (rect.x + m, rect.y + ts // 2 - 1, ts - 2 * m, 2))
            pygame.draw.rect(self.surf, settings.COLOR_TARGET,
                             (rect.x + ts // 2 - 1, rect.y + m, 2, ts - 2 * m))

    def _draw_box(self, gx: int, gy: int, on_target: bool,
                  offset_x: int, offset_y: int) -> None:
        ts     = settings.TILE_SIZE
        bounce = self._box_bounces.get((gx, gy), 0)
        scale  = 1.0 + 0.15 * math.sin(
            bounce / settings.BOX_BOUNCE_FRAMES * math.pi
        ) if bounce > 0 else 1.0

        color  = settings.COLOR_BOX_DONE if on_target else settings.COLOR_BOX

        # Scaled size (centred in cell)
        sw = max(1, int(ts * scale))
        sh = max(1, int(ts * scale))
        sx = offset_x + gx * ts + (ts - sw) // 2
        sy = offset_y + gy * ts + (ts - sh) // 2

        pygame.draw.rect(self.surf, color, (sx, sy, sw, sh))
        # Bevel
        pygame.draw.line(self.surf, settings.WHITE,
                         (sx, sy), (sx + sw - 1, sy))
        pygame.draw.line(self.surf, settings.WHITE,
                         (sx, sy), (sx, sy + sh - 1))
        pygame.draw.line(self.surf, settings.BLACK,
                         (sx, sy + sh - 1), (sx + sw - 1, sy + sh - 1))
        pygame.draw.line(self.surf, settings.BLACK,
                         (sx + sw - 1, sy), (sx + sw - 1, sy + sh - 1))

        if on_target:
            # Small check mark / dot
            cx2, cy2 = sx + sw // 2, sy + sh // 2
            pygame.draw.rect(self.surf, settings.DARK_GREEN,
                             (cx2 - 2, cy2 - 2, 4, 4))

    def _draw_player(self, player: Player,
                     offset_x: int, offset_y: int) -> None:
        ts    = settings.TILE_SIZE
        gx, gy = player.grid_x, player.grid_y
        rx = offset_x + gx * ts
        ry = offset_y + gy * ts

        # Body
        pygame.draw.rect(self.surf, settings.COLOR_PLAYER,
                         (rx + 3, ry + 4, ts - 6, ts - 5))
        # Head
        pygame.draw.rect(self.surf, settings.COLOR_PLAYER,
                         (rx + 4, ry + 1, ts - 8, 4))

        # Eyes (direction-dependent)
        face = player.facing
        if face == FACE_RIGHT:
            pygame.draw.rect(self.surf, settings.BLACK, (rx + 9, ry + 2, 2, 2))
        elif face == FACE_LEFT:
            pygame.draw.rect(self.surf, settings.BLACK, (rx + 5, ry + 2, 2, 2))
        elif face == FACE_DOWN:
            pygame.draw.rect(self.surf, settings.BLACK, (rx + 5, ry + 3, 2, 2))
            pygame.draw.rect(self.surf, settings.BLACK, (rx + 9, ry + 3, 2, 2))
        else:  # UP — show back of head
            pass

        # Walk animation: alternate legs
        frame = player.walk_frame
        if frame % 2 == 0:
            pygame.draw.rect(self.surf, settings.COLOR_PLAYER,
                             (rx + 4, ry + ts - 3, 3, 3))
            pygame.draw.rect(self.surf, settings.DARK_GRAY,
                             (rx + ts - 7, ry + ts - 3, 3, 3))
        else:
            pygame.draw.rect(self.surf, settings.DARK_GRAY,
                             (rx + 4, ry + ts - 3, 3, 3))
            pygame.draw.rect(self.surf, settings.COLOR_PLAYER,
                             (rx + ts - 7, ry + ts - 3, 3, 3))

    # ── Level rendering ───────────────────────────────────────────────────────

    def draw_level(self, level: Level, player: Player) -> None:
        ts    = settings.TILE_SIZE
        game_h = self.h - settings.HUD_HEIGHT

        # Centre the level grid in the game area
        offset_x = (self.w       - level.width  * ts) // 2
        offset_y = (game_h - level.height * ts) // 2
        offset_y = max(0, offset_y)

        # Apply shake offset
        offset_x += player.shake_offset[0]
        offset_y += player.shake_offset[1]

        # Background fill
        self.surf.fill(settings.COLOR_BG)

        # Draw tiles
        for gy in range(level.height):
            for gx in range(level.width):
                self._draw_tile(gx, gy, level.tiles[gy][gx], offset_x, offset_y)

        # Draw boxes
        for bx, by in level.boxes:
            on_target = (bx, by) in level.targets
            self._draw_box(bx, by, on_target, offset_x, offset_y)

        # Draw player
        self._draw_player(player, offset_x, offset_y)

        # Update & draw particles
        dead = []
        for i, p in enumerate(self._particles):
            p.update()
            if p.alive:
                p.draw(self.surf)
            else:
                dead.append(i)
        for i in reversed(dead):
            self._particles.pop(i)

        # Update box bounces
        expired = [k for k, v in self._box_bounces.items() if v <= 0]
        for k in expired:
            del self._box_bounces[k]
        for k in self._box_bounces:
            self._box_bounces[k] -= 1

        # CRT overlay
        if self._crt_enabled:
            self.surf.blit(self._crt_overlay, (0, 0))
            self.surf.blit(self._vignette, (0, 0))

    # ── Effects ───────────────────────────────────────────────────────────────

    def spawn_particles(self, gx: int, gy: int,
                        offset_x: int = 0, offset_y: int = 0) -> None:
        ts  = settings.TILE_SIZE
        cx  = offset_x + gx * ts + ts // 2
        cy  = offset_y + gy * ts + ts // 2
        for _ in range(settings.PARTICLE_COUNT):
            self._particles.append(Particle(cx, cy))

    def trigger_box_bounce(self, gx: int, gy: int) -> None:
        self._box_bounces[(gx, gy)] = settings.BOX_BOUNCE_FRAMES

    def set_crt(self, enabled: bool) -> None:
        self._crt_enabled = enabled

    def apply_crt_rects(self, surf: pygame.Surface, rects: list) -> None:
        """Apply CRT scanline+vignette only to the given rects on `surf`."""
        if not self._crt_enabled:
            return
        w, h = surf.get_size()
        crt = pygame.transform.scale(self._crt_overlay, (w, h))
        vig = pygame.transform.scale(self._vignette,    (w, h))
        for rect in rects:
            surf.blit(crt, rect.topleft, rect)
            surf.blit(vig, rect.topleft, rect)

    # ── Utility ──────────────────────────────────────────────────────────────

    def level_offset(self, level: Level) -> Tuple[int, int]:
        """Return (offset_x, offset_y) used to position the level grid."""
        ts     = settings.TILE_SIZE
        game_h = self.h - settings.HUD_HEIGHT
        ox = (self.w       - level.width  * ts) // 2
        oy = (game_h - level.height * ts) // 2
        return max(0, ox), max(0, oy)
