from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Logger,Direction
from src.core import GameManager
import math
from typing import override
import copy

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)    
        self.teleport_cooldown = 0.0
        self.next_teleport_pos: Position | None = None 
    #pc
    def is_facing_pc(self):
        
        TILE = GameSettings.TILE_SIZE

        # Player's collision box (use a rect around the player)
        player_rect = pg.Rect(
            self.position.x,
            self.position.y,
            TILE,
            TILE
        )

        # Check if player is adjacent to any PC tile
        for pc_rect in self.game_manager.current_map.pc_tiles:
            rect = copy.deepcopy(pc_rect)
            rect.y += TILE
            # Check touching from any of 4 sides
            if player_rect.colliderect(rect):
                return True
        return False
    #npc shop
    def try_interact_with_npc(self):
        TILE = GameSettings.TILE_SIZE

        player_rect = pg.Rect(
            self.position.x,
            self.position.y,
            TILE,
            TILE
        )

        
        if hasattr(self.game_manager.current_map, "npcs"):
            for npc in self.game_manager.current_map.npcs:
                nx = npc.position.x
                ny = npc.position.y + TILE
                rect = pg.Rect(
                    nx,ny,TILE,TILE
                )
                if player_rect.colliderect(rect):
                    npc.interact()
                    return
    @override
    def update(self, dt: float) -> None:
        dis = Position(0, 0)
        self.is_moving = False
        if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
            dis.y -= 1
            self.direction = Direction.UP
            self.is_moving = True
        if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
            dis.y += 1
            self.direction = Direction.DOWN
            self.is_moving = True
        if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
            dis.x -= 1
            self.direction = Direction.LEFT
            self.is_moving = True
        if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
            dis.x += 1
            self.direction = Direction.RIGHT
            self.is_moving = True
        
        
        if dis.x != 0 or dis.y != 0:
            length = math.sqrt(dis.x * dis.x + dis.y * dis.y)
            dis.x /= length
            dis.y /= length
            dis.x *= self.speed * dt
            dis.y *= self.speed * dt
            
        rect = self.get_rect()

       
        rect.x += dis.x
        if self.game_manager.check_collision(rect):
            rect.x -= dis.x
            rect.x = self._snap_to_grid(rect.x)

       
        rect.y += dis.y
        if self.game_manager.check_collision(rect):
            rect.y -= dis.y
            rect.y = self._snap_to_grid(rect.y)

        
        self.position.x = rect.x
        self.position.y = rect.y

        if input_manager.key_pressed(pg.K_f):
            if self.is_facing_pc():
                self.game_manager.pc_box.open(self.game_manager)
        if input_manager.key_pressed(pg.K_f):
            self.try_interact_with_npc()

        self.animation.set_state(self.direction.name.lower())
        if self.is_moving :
            self.animation.play()
        else:
            self.animation.stop()
            self.animation.set_frame(0)
            
            
        '''
        
        [TODO HACKATHON 4]
        Check if there is collision, if so try to make the movement smooth
        Hint #1 : use entity.py _snap_to_grid function or create a similar function
        Hint #2 : Beware of glitchy teleportation, you must do
                    1. Update X
                    2. If collide, snap to grid
                    3. Update Y
                    4. If collide, snap to grid
                  instead of update both x, y, then snap to grid
        
        
        
        self.position = ...
        '''
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt
        else:
            tp = self.game_manager.current_map.check_teleport(self.position)
            if tp:
                dest = tp.destination
                if dest in self.game_manager.maps:
                    if hasattr(tp, "dest_pos") and tp.dest_pos is not None:
                        self.next_teleport_pos = tp.dest_pos.copy()
                    else:
                        self.next_teleport_pos = None
                    self.game_manager.switch_map(dest)
                    self.teleport_cooldown = 1.0
                    
        self.animation.set_state(self.direction.name.lower())
        if self.is_moving:
            self.animation.play()
        else:
            self.animation.stop()
            self.animation.set_frame(0)
        super().update(dt)


    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)

