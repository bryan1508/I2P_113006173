import pygame as pg
import pytmx

from src.utils import load_tmx, Position, GameSettings, PositionCamera, Teleport

class Map:
    # Map Properties
    path_name: str
    tmxdata: pytmx.TiledMap
    # Position Argument
    spawn: Position
    teleporters: list[Teleport]
    # Rendering Properties
    _surface: pg.Surface
    _collision_map: list[pg.Rect]

    def __init__(self, path: str, tp: list[Teleport], spawn: Position):
        self.path_name = path
        self.tmxdata = load_tmx(path)
        self.spawn = spawn
        self.teleporters = tp
        self.bush_tiles = self._load_bush_tiles()

        self.pixel_w = self.tmxdata.width * GameSettings.TILE_SIZE
        self.pixel_h = self.tmxdata.height * GameSettings.TILE_SIZE

        
        self._surface = pg.Surface((self.pixel_w, self.pixel_h), pg.SRCALPHA)
        self._render_all_layers(self._surface)
        
        self._collision_map = self._create_collision_map()
        self.pc_tiles = self._load_pc_tiles()
        self.npcs = []
    def _load_pc_tiles(self):
        pcs = []
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and "collisionpc" in layer.name.lower():
                for x, y, gid in layer:
                    if gid != 0:
                        pcs.append(pg.Rect(
                            x * GameSettings.TILE_SIZE,
                            y * GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE,
                            GameSettings.TILE_SIZE
                        ))
        return pcs
    def _load_bush_tiles(self):
        bushes = []
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and "bush" in layer.name.lower():
                for x, y, gid in layer:
                    if gid != 0:
                        bushes.append(
                            pg.Rect(
                                x * GameSettings.TILE_SIZE,
                                y * GameSettings.TILE_SIZE,
                                GameSettings.TILE_SIZE,
                                GameSettings.TILE_SIZE
                            )
                        )
        return bushes
    
    
    def check_bush(self, position):
        px, py = position.x+ GameSettings.TILE_SIZE // 2, position.y+ GameSettings.TILE_SIZE // 2
        for rect in self.bush_tiles:
            if rect.collidepoint(px,py):
                return True
        return False
    def update(self, dt: float):
        return

    def draw(self, screen: pg.Surface, camera: PositionCamera):
        screen.blit(self._surface, camera.transform_position(Position(0, 0)))
        
        # Draw the hitboxes collision map
        if GameSettings.DRAW_HITBOXES:
            for rect in self._collision_map:
                pg.draw.rect(screen, (255, 0, 0), camera.transform_rect(rect), 1)
        
    def check_collision(self, rect: pg.Rect) -> bool:
        for hitbox in self._collision_map:
            if(rect.colliderect(hitbox)):
                return True
        return False
        '''
        [TODO HACKATHON 4]
        Return True if collide if rect param collide with self._collision_map
        Hint: use API colliderect and iterate each rectangle to check
        '''
        return False
        
    def check_teleport(self, pos: Position) -> Teleport | None:
        for tp in self.teleporters:
            tp_rect = pg.Rect(
                tp.pos.x,
                tp.pos.y,
                GameSettings.TILE_SIZE,
                GameSettings.TILE_SIZE
            )
            if tp_rect.collidepoint(pos.x, pos.y):
                return tp
        return None 
        '''[TODO HACKATHON 6] 
        Teleportation: Player can enter a building by walking into certain tiles defined inside saves/*.json, and the map will be changed
        Hint: Maybe there is an way to switch the map using something from src/core/managers/game_manager.py called switch_... 
        '''
        return None

    def _render_all_layers(self, target: pg.Surface) -> None:
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(target, layer)
            # elif isinstance(layer, pytmx.TiledImageLayer) and layer.image:
            #     target.blit(layer.image, (layer.x or 0, layer.y or 0))
 
    def _render_tile_layer(self, target: pg.Surface, layer: pytmx.TiledTileLayer) -> None:
        for x, y, gid in layer:
            if gid == 0:
                continue
            image = self.tmxdata.get_tile_image_by_gid(gid)
            if image is None:
                continue

            image = pg.transform.scale(image, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
            target.blit(image, (x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE))
    
    def _create_collision_map(self) -> list[pg.Rect]:
        rects = []
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and ("collision" in layer.name.lower() or "house" in layer.name.lower()):
                for x, y, gid in layer:
                    if gid != 0:
                        rects.append(
                            pg.Rect(
                                x * GameSettings.TILE_SIZE,
                                y * GameSettings.TILE_SIZE,
                                GameSettings.TILE_SIZE,
                                GameSettings.TILE_SIZE
                            )
                        )
                        '''
                        [TODO HACKATHON 4]
                        rects.append(pg.Rect(...))
                        Append the collision rectangle to the rects[] array
                        Remember scale the rectangle with the TILE_SIZE from settings
                        '''
                        pass
        return rects

    @classmethod
    def from_dict(cls, data: dict) -> "Map":
        from src.entities.shop_npc import ShopNPC  # import here to avoid circular import

        tp = [Teleport.from_dict(t) for t in data["teleport"]]
        pos = Position(
            data["player"]["x"] * GameSettings.TILE_SIZE,
            data["player"]["y"] * GameSettings.TILE_SIZE
        )

        # Create map object
        map_obj = cls(data["path"], tp, pos)

        # ⭐ Load NPCs
        if "npcs" in data:
            TILE = GameSettings.TILE_SIZE
            for npc_data in data["npcs"]:
                npc_type = npc_data.get("type", "")

                if npc_type == "shop":
                    npc = ShopNPC(
                        npc_data["x"] * TILE,
                        npc_data["y"] * TILE,
                        gm=None  # game_manager will be assigned later by GameManager
                    )
                    map_obj.npcs.append(npc)

        return map_obj
    def to_dict(self):
        data = {
            "path": self.path_name,
            "teleport": [t.to_dict() for t in self.teleporters],
            "player": {
                "x": self.spawn.x // GameSettings.TILE_SIZE,
                "y": self.spawn.y // GameSettings.TILE_SIZE,
            }
        }

        # ⭐ Save NPCs
        if hasattr(self, "npcs"):
            data["npcs"] = []
            TILE = GameSettings.TILE_SIZE
            for npc in self.npcs:
                data["npcs"].append({
                    "type": npc.__class__.__name__.lower().replace("npc", ""),
                    "x": int(npc.position.x // TILE),
                    "y": int(npc.position.y // TILE)
                })

        return data