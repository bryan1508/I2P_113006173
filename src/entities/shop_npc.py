from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.data.shop import Shop, ShopItem
from src.utils import GameSettings

class ShopNPC(Entity):
    def __init__(self, x, y, gm):
        super().__init__(x, y, gm)
        self.shop = Shop([
            ShopItem("Heal Potion", 2, "ingame_ui/heal.png"),
            ShopItem("Strength Potion", 2, "ingame_ui/strength.png"),
            ShopItem("Defense Potion", 2, "ingame_ui/defense.png"),
            ShopItem("Pokeball", 3, "ingame_ui/ball.png"),
        ])

    def interact(self):
        self.game_manager.open_shop(self.shop)

    def update(self, dt):
        pass