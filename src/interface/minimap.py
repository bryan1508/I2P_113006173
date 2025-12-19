import pygame as pg
from src.utils import GameSettings


class Minimap:
    def __init__(self, game_map, player, max_height=150):
        """
        game_map : Map
        player   : Player
        max_height : maximum minimap height in pixels
        """

        self.map = game_map
        self.player = player

        # --- DYNAMIC MINIMAP SIZE BASED ON REAL MAP RATIO ---
        self.h = max_height
        self.w = int(self.h * (self.map.pixel_w / self.map.pixel_h))

        # Create scaled minimap surface once
        self.minimap_surface = pg.transform.smoothscale(
            self.map._surface,
            (self.w, self.h)
        )

        # Scaling factors (world → minimap)
        self.scale_x = self.w / self.map.pixel_w
        self.scale_y = self.h / self.map.pixel_h

        # Minimap screen position
        self.x = 10
        self.y = 10

        # Marker colors
        self.player_color = (0, 255, 255)   # cyan
        self.shop_color = (255, 255, 0)     # yellow
        self.enemy_color = (255, 0, 0)      # red

        self.radius = 3

        #enemy
        self.enemy_trainers = None
    #get enemy trainer(game scene)
    def update_enemy_trainers(self, trainers):
        self.enemy_trainers = trainers
    # -------------------------------------------------------------------------
    def update_map(self, new_map):
        """Rebuild minimap when switching maps."""
        self.map = new_map

        # Recompute minimap dimensions
        self.w = int(self.h * (new_map.pixel_w / new_map.pixel_h))

        # Recreate scaled minimap
        self.minimap_surface = pg.transform.smoothscale(
            new_map._surface,
            (self.w, self.h)
        )

        # Update scaling
        self.scale_x = self.w / new_map.pixel_w
        self.scale_y = self.h / new_map.pixel_h

    # -------------------------------------------------------------------------
    def draw_npcs(self, screen):
        """
        Draw NPCs:
        - Shop NPCs: map.npcs (yellow)
        - Trainers: map.enemy_trainers (red)
        """

        # ----- Shop NPCs -----
        for npc in getattr(self.map, "npcs", []):
            px = int(npc.position.x * self.scale_x) + self.x
            py = int(npc.position.y * self.scale_y) + self.y
            pg.draw.circle(screen, self.shop_color, (px, py), self.radius)

        # ----- Enemy Trainers -----
        if self.enemy_trainers:
            for trainer in self.enemy_trainers:

                world_x = trainer.position.x
                world_y = trainer.position.y

                px = int(world_x * self.scale_x) + self.x
                py = int(world_y * self.scale_y) + self.y

                pg.draw.circle(screen, self.enemy_color, (px, py), self.radius)

    # -------------------------------------------------------------------------
    def draw(self, screen):

        # 1. Draw minimap base
        screen.blit(self.minimap_surface, (self.x, self.y))

        # 2. Black outline frame
        pg.draw.rect(
            screen,
            (0, 0, 0),
            pg.Rect(self.x, self.y, self.w, self.h),
            width=2
        )

        # 3. Draw NPCs
        self.draw_npcs(screen)

        # 4. Draw player
        world_x = self.player.position.x
        world_y = self.player.position.y

        px = int(world_x * self.scale_x) + self.x
        py = int(world_y * self.scale_y) + self.y

        pg.draw.circle(screen, self.player_color, (px, py), self.radius)
