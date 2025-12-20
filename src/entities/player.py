from __future__ import annotations

import copy
import math
from collections import deque
from typing import override

import pygame as pg

from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Direction
from src.core import GameManager


class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)

        self.teleport_cooldown = 0.0
        self.next_teleport_pos: Position | None = None

        # Navigation state
        self.nav_path_tiles: list[tuple[int, int]] = []
        self.nav_auto_move: bool = False
        # Threshold to account for speed/dt variance
        self.nav_stop_distance_px: float = 4.0 

    # -------------------------
    # PC / NPC interaction
    # -------------------------
    def is_facing_pc(self):
        TILE = GameSettings.TILE_SIZE
        player_rect = self.get_rect()

        for pc_rect in self.game_manager.current_map.pc_tiles:
            rect = copy.deepcopy(pc_rect)
            rect.y += TILE
            if player_rect.colliderect(rect):
                return True
        return False

    def try_interact_with_npc(self):
        TILE = GameSettings.TILE_SIZE
        player_rect = self.get_rect()

        if hasattr(self.game_manager.current_map, "npcs"):
            for npc in self.game_manager.current_map.npcs:
                nx = npc.position.x
                ny = npc.position.y + TILE
                rect = pg.Rect(nx, ny, TILE, TILE)
                if player_rect.colliderect(rect):
                    npc.interact()
                    return

    # -------------------------
    # Navigation (BFS -> teleport tile)
    # -------------------------
    def cancel_navigation(self) -> None:
        self.nav_path_tiles = []
        self.nav_auto_move = False

    def _is_walkable_tile(self, tx: int, ty: int) -> bool:
        TILE = GameSettings.TILE_SIZE
        m = self.game_manager.current_map
        
        # 1. Basic boundary check
        w, h = getattr(m, "width", None), getattr(m, "height", None)
        if isinstance(w, int) and isinstance(h, int):
            max_tx, max_ty = (w // TILE, h // TILE) if w > 512 else (w, h)
            if tx < 0 or ty < 0 or tx >= max_tx or ty >= max_ty:
                return False

        # 2. Check for solid collisions (Walls, Houses)
        rect = pg.Rect(tx * TILE, ty * TILE, TILE, TILE)
        if self.game_manager.check_collision(rect):
            return False

        # 3. Avoid Bushes (Preventing catch scenes during auto-navigation)
        # We use a Position object because your Map.check_bush expects one
        test_pos = Position(tx * TILE, ty * TILE)
        if m.check_bush(test_pos):
            return False

        return True

    def _bfs_to_destination_teleport(self, dest_map: str) -> list[tuple[int, int]]:
        TILE = GameSettings.TILE_SIZE
        start = (int(self.position.x // TILE), int(self.position.y // TILE))

        q = deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        MAX_VISITS = 40000
        visits = 0

        while q:
            cx, cy = q.popleft()
            visits += 1
            if visits > MAX_VISITS: break

            wp = Position(cx * TILE, cy * TILE)
            tp = self.game_manager.current_map.check_teleport(wp)
            if tp and getattr(tp, "destination", None) == dest_map:
                path: list[tuple[int, int]] = []
                cur: tuple[int, int] | None = (cx, cy)
                while cur is not None and cur != start:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                return path

            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                if (nx, ny) not in came_from and self._is_walkable_tile(nx, ny):
                    came_from[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))
        return []

    def start_navigation_to_map(self, map_name: str, auto_move: bool = True) -> None:
        if not self.game_manager.current_map or map_name == self.game_manager.current_map.path_name:
            self.cancel_navigation()
            return

        path = self._bfs_to_destination_teleport(map_name)
        if not path:
            self.cancel_navigation()
            return

        self.nav_path_tiles = path
        self.nav_auto_move = auto_move

    def _step_navigation(self, dt: float) -> Position:
        if not self.nav_auto_move or not self.nav_path_tiles:
            return Position(0, 0)

        TILE = GameSettings.TILE_SIZE
        tx, ty = self.nav_path_tiles[0]
        
        # Target the center of the tile
        target_x = (tx * TILE) + (TILE // 2) - (self.get_rect().width // 2)
        target_y = (ty * TILE) + (TILE // 2) - (self.get_rect().height // 2)

        dx = target_x - self.position.x
        dy = target_y - self.position.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= self.nav_stop_distance_px:
            self.position.x = target_x
            self.position.y = target_y
            self.nav_path_tiles.pop(0)
            if not self.nav_path_tiles:
                self.nav_auto_move = False
            return Position(0, 0)

        vx, vy = dx / dist, dy / dist
        if abs(dx) > abs(dy):
            self.direction = Direction.RIGHT if dx > 0 else Direction.LEFT
        else:
            self.direction = Direction.DOWN if dy > 0 else Direction.UP

        return Position(vx, vy)

    # -------------------------
    # Update
    # -------------------------
    @override
    def update(self, dt: float) -> None:
        # 1. Check for manual override
        manual_keys = (pg.K_UP, pg.K_w, pg.K_DOWN, pg.K_s, pg.K_LEFT, pg.K_a, pg.K_RIGHT, pg.K_d)
        if any(input_manager.key_down(k) for k in manual_keys) and self.nav_auto_move:
            self.cancel_navigation()

        # 2. Determine Movement Vector
        dis = Position(0, 0)
        self.is_moving = False

        nav_vec = self._step_navigation(dt)
        if nav_vec.x != 0 or nav_vec.y != 0:
            dis = nav_vec
            self.is_moving = True
        else:
            # Manual movement logic
            if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
                dis.y -= 1; self.direction = Direction.UP; self.is_moving = True
            if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
                dis.y += 1; self.direction = Direction.DOWN; self.is_moving = True
            if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
                dis.x -= 1; self.direction = Direction.LEFT; self.is_moving = True
            if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
                dis.x += 1; self.direction = Direction.RIGHT; self.is_moving = True

        # Apply speed and dt
        if dis.x != 0 or dis.y != 0:
            length = math.sqrt(dis.x**2 + dis.y**2)
            dis.x = (dis.x / length) * self.speed * dt
            dis.y = (dis.y / length) * self.speed * dt

        # 3. Collision with Axis Snapping (Original Logic)
        rect = self.get_rect()
        
        # X-Axis
        rect.x += dis.x
        if self.game_manager.check_collision(rect):
            rect.x -= dis.x
            rect.x = self._snap_to_grid(rect.x)
        
        # Y-Axis
        rect.y += dis.y
        if self.game_manager.check_collision(rect):
            rect.y -= dis.y
            rect.y = self._snap_to_grid(rect.y)
            
        self.position.x, self.position.y = rect.x, rect.y

        # 4. Interaction & Teleport
        if input_manager.key_pressed(pg.K_f):
            if self.is_facing_pc(): 
                self.game_manager.pc_box.open(self.game_manager)
            self.try_interact_with_npc()

        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt
        else:
            tp = self.game_manager.current_map.check_teleport(self.position)
            if tp:
                self.cancel_navigation()
                dest = tp.destination
                if dest in self.game_manager.maps:
                    self.next_teleport_pos = tp.dest_pos.copy() if hasattr(tp, "dest_pos") and tp.dest_pos else None
                    self.game_manager.switch_map(dest)
                    self.teleport_cooldown = 1.0

        # 5. Animation
        self.animation.set_state(self.direction.name.lower())
        if self.is_moving:
            self.animation.play()
        else:
            self.animation.stop()
            self.animation.set_frame(0)

        super().update(dt)

    # -------------------------
    # Draw logic
    # -------------------------
    def _world_to_screen(self, wx: float, wy: float, camera: PositionCamera) -> tuple[int, int]:
        return (int(wx - camera.x), int(wy - camera.y))

    def draw_navigation_path(self, screen: pg.Surface, camera: PositionCamera) -> None:
        if not self.nav_path_tiles: return
        TILE = GameSettings.TILE_SIZE
        tri_len, tri_w = int(TILE * 0.45), int(TILE * 0.35)
        prev_x, prev_y = self.position.x, self.position.y

        for (tx, ty) in self.nav_path_tiles:
            px, py = tx * TILE, ty * TILE
            dx, dy = px - prev_x, py - prev_y
            
            # Decide arrow direction based on path flow
            if abs(dx) > abs(dy):
                dir_vec = (1, 0) if dx > 0 else (-1, 0)
            else:
                dir_vec = (0, 1) if dy > 0 else (0, -1)

            cx, cy = px + TILE * 0.5, py + TILE * 0.5
            sx, sy = self._world_to_screen(cx, cy, camera)
            vx, vy = dir_vec
            
            tip = (sx + vx * tri_len * 0.5, sy + vy * tri_len * 0.5)
            bx, by = sx - vx * tri_len * 0.5, sy - vy * tri_len * 0.5
            pxv, pyv = -vy, vx # Perpendicular
            
            left = (bx + pxv * tri_w * 0.5, by + pyv * tri_w * 0.5)
            right = (bx - pxv * tri_w * 0.5, by - pyv * tri_w * 0.5)

            pg.draw.polygon(screen, (255, 0, 0), [tip, left, right])
            prev_x, prev_y = px, py

    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        self.draw_navigation_path(screen, camera)
        super().draw(screen, camera)

    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> "Player":
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)