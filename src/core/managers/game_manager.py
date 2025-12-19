from __future__ import annotations
from src.utils import Logger, GameSettings, Position, Teleport
from src.core.services import sound_manager
import json, os
import pygame as pg
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.maps.map import Map
    from src.entities.player import Player
    from src.entities.enemy_trainer import EnemyTrainer
    from src.data.bag import Bag
    from src.data.pc_box import PCBox

class GameManager:
    # Entities
    player: Player | None
    enemy_trainers: dict[str, list[EnemyTrainer]]
    bag: "Bag"
    pc_box : "PCBox"
    # Map properties
    current_map_key: str
    maps: dict[str, Map]
    
    # Changing Scene properties
    should_change_scene: bool
    next_map: str
    
    def __init__(self, maps: dict[str, Map], start_map: str, 
                 player: Player | None,
                 enemy_trainers: dict[str, list[EnemyTrainer]], 
                 bag: Bag ,pc_box :PCBox| None = None):
        from src.data.pc_box import PCBox               
        from src.data.bag import Bag
        # Game Properties
        self.player_spawns = {}
        self.maps = maps
        self.current_map_key = start_map
        self.player = player
        self.enemy_trainers = enemy_trainers
        self.bag = bag if bag is not None else Bag([], [])
        self.pc_box = pc_box if pc_box is not None else PCBox([])
        
        # Check If you should change scene
        self.should_change_scene = False
        self.next_map = ""
        self.current_shop_overlay = None
        
    @property
    def current_map(self) -> Map:
        return self.maps[self.current_map_key]
        
    @property
    def current_enemy_trainers(self) -> list[EnemyTrainer]:
        return self.enemy_trainers[self.current_map_key]
        
    @property
    def current_teleporter(self) -> list[Teleport]:
        return self.maps[self.current_map_key].teleporters
    
    def switch_map(self, target: str) -> None:
        if target not in self.maps:
            Logger.warning(f"Map '{target}' not loaded; cannot switch.")
            return
        
        self.next_map = target
        self.should_change_scene = True 
            
    def try_switch_map(self) -> None:
        if self.should_change_scene:
            self.current_map_key = self.next_map
            self.next_map = ""
            self.should_change_scene = False
            if self.player:
                if getattr(self.player, "next_teleport_pos", None):
                    self.player.position = self.player.next_teleport_pos.copy()
                    self.player.next_teleport_pos = None
                else:
                    self.player.position = self.maps[self.current_map_key].spawn

                self.player.teleport_cooldown = 0.5
            
    def check_collision(self, rect: pg.Rect) -> bool:
        if self.maps[self.current_map_key].check_collision(rect):
            return True
        for entity in self.enemy_trainers[self.current_map_key]:
            if rect.colliderect(entity.animation.rect):
                return True
        npc_list = getattr(self.current_map, "npcs", [])
        for npc in npc_list:
            if rect.colliderect(npc.get_rect()):
                return True

        return False
    
    #shop
    def open_shop(self, shop):
        from src.interface.shop_overlay import ShopOverlay
        self.current_shop_overlay = ShopOverlay(shop, self.bag)
    def close_shop(self):
        self.current_shop_overlay = None

        
    def save(self, path: str) -> None:
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            Logger.info(f"Game saved to {path}")
        except Exception as e:
            Logger.warning(f"Failed to save game: {e}")
             
    @classmethod
    def load(cls, path: str) -> "GameManager | None":
        if not os.path.exists(path):
            Logger.error(f"No file found: {path}, ignoring load function")
            return None

        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, object]:
        map_blocks: list[dict[str, object]] = []
        for key, m in self.maps.items():
            block = m.to_dict()
            block["enemy_trainers"] = [t.to_dict() for t in self.enemy_trainers.get(key, [])]
            
            map_blocks.append(block)
        return {
            "map": map_blocks,
            "current_map": self.current_map_key,
            "player": self.player.to_dict() if self.player is not None else None,
            "bag": self.bag.to_dict(),
            "pc_box": self.pc_box.to_dict(),
            "audio_volume": GameSettings.AUDIO_VOLUME,
            "audio_muted": GameSettings.AUDIO_MUTED,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GameManager":
        from src.maps.map import Map
        from src.entities.player import Player
        from src.entities.enemy_trainer import EnemyTrainer
        from src.data.bag import Bag
        
        Logger.info("Loading maps")
        maps_data = data["map"]
        maps: dict[str, Map] = {}
        player_spawns: dict[str, Position] = {}
        trainers: dict[str, list[EnemyTrainer]] = {}

        for entry in maps_data:
            path = entry["path"]
            maps[path] = Map.from_dict(entry)
            sp = entry.get("player")
            if sp:
                player_spawns[path] = Position(
                    sp["x"] * GameSettings.TILE_SIZE,
                    sp["y"] * GameSettings.TILE_SIZE
                )
        current_map = data["current_map"]
        gm = cls(
            maps, current_map,
            None, # Player
            trainers,
            bag=None
        )
        gm.current_map_key = current_map
        
        Logger.info("Loading enemy trainers")
        for m in data["map"]:
            raw_data = m["enemy_trainers"]
            gm.enemy_trainers[m["path"]] = [EnemyTrainer.from_dict(t, gm) for t in raw_data]
        
        Logger.info("Loading Player")
        if data.get("player"):
            gm.player = Player.from_dict(data["player"], gm)
        
        Logger.info("Loading bag")
        from src.data.bag import Bag as _Bag
        gm.bag = Bag.from_dict(data.get("bag", {})) if data.get("bag") else _Bag([], [])
        from src.data.pc_box import PCBox
        gm.pc_box = PCBox.from_dict(data.get("pc_box", []))

        #get volume and muted status

        GameSettings.AUDIO_VOLUME = data.get("audio_volume", GameSettings.AUDIO_VOLUME)
        GameSettings.AUDIO_MUTED = data.get("audio_muted", GameSettings.AUDIO_MUTED)

        # Apply volume to mixer if BGM is playing
        if sound_manager.current_bgm:
            sound_manager.current_bgm.set_volume(GameSettings.AUDIO_VOLUME)

        if GameSettings.AUDIO_MUTED:
            sound_manager.pause_all()
        else:
            sound_manager.resume_all()

        for m in gm.maps.values():
            if hasattr(m, "npcs"):
                for npc in m.npcs:
                    npc.game_manager = gm
        return gm