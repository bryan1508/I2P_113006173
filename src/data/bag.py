import pygame as pg
import json
from src.utils import GameSettings,Position
from src.utils.definition import Monster, Item
from src.interface.components import Button
from src.core.services import input_manager
from src.sprites import Sprite


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []
        self.visible = False
        self.scroll = 0
        self.scroll_speed = 20
        self.max_scroll = 0
        self.scroll_area = pg.Rect(650, 200, 230, 360)
        #element
        self.element_icons = {
            "Fire": "element/fire.png",
            "Water": "element/water.png",
            "Grass": "element/grass.png",
            "Normal": "element/normal.png"
        }

        # Close button
        self.close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            GameSettings.SCREEN_WIDTH // 2 + 215,
            GameSettings.SCREEN_HEIGHT // 2 - 230,
            40, 40,
            self.toggle
        )
        self.font_title = pg.font.Font(None, 50)
        self.font_small = pg.font.Font(None, 21)
        self.font_tiny = pg.font.Font(None, 18)
    def use_pokeball(self):
        for item in self._items_data:
            if item["name"].lower() == "pokeball":
                if item["count"] > 0:
                    item["count"] -= 1
                    return True
                else:
                    return False
        return False
    #for shop
    def _add_or_increase(self, name, sprite_path=None, amount=1):
        for it in self._items_data:
            if it["name"] == name:
                it["count"] += amount
                return
        # if not found
        self._items_data.append({
            "name": name,
            "count": amount,
            "sprite_path": sprite_path
        })
        
    def toggle(self):
        self.visible = not self.visible
        self.scroll = 0

    def update(self, dt):
        if not self.visible:
            return

        self.close_button.update(dt)
        mx,my = pg.mouse.get_pos()
        mouse_wheel = input_manager.mouse_wheel
        if self.scroll_area.collidepoint(mx,my):
            if mouse_wheel != 0 :
            
                self.scroll += mouse_wheel * self.scroll_speed
                # Clamp scroll so we don’t scroll too far
                self.scroll = min(0,max(self.scroll,self.max_scroll)) 
        

    def draw(self, screen: pg.Surface):
        if not self.visible:
            return
        # --- Dim background ---
        dim = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # Panel
        panel_width, panel_height = 550, 500
        panel_x = (GameSettings.SCREEN_WIDTH - panel_width) // 2
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_height) // 2
        panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)

        # Shadow
        pg.draw.rect(screen, (50, 50, 50), panel_rect.move(6, 6), border_radius=20)
        pg.draw.rect(screen, (255, 165, 0), panel_rect, border_radius=20)
        pg.draw.rect(screen, (0, 0, 0), panel_rect, 3, border_radius=20)

        # Title
        title = self.font_title.render("Bag", True, (0, 0, 0))
        screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 30))
        #close button
        self.close_button.draw(screen)

        #monster 
        y_offset = panel_y + 82
        for monster in self._monsters_data:
            #monster white box
            card = pg.Rect(panel_x + 25, y_offset, 230, 60)
            pg.draw.rect(screen, (255, 255, 255), card, border_radius=10)
            pg.draw.rect(screen, (0, 0, 0), card, 2, border_radius=10)
            #monster image 
            sprite = Sprite("ingame_ui/"+monster["sprite_path"],(45, 45))
            sprite.update_pos(Position(card.left + 15, card.centery - 26))
            sprite.draw(screen)
            # --- Element Icon ---
            element_type = monster.get("type", None)
            if element_type in self.element_icons:
                icon_path = self.element_icons[element_type]
                elem_icon = Sprite(icon_path, (22, 22))
                elem_icon.update_pos(Position(card.right - 30, card.top + 3))
                elem_icon.draw(screen)
            #monster name
            name = self.font_small.render(monster["name"], True, (0, 0, 0))
            screen.blit(name, (card.left + 80, card.top + 7))
            #level
            level = self.font_small.render(f"Lv.{monster['level']}", True, (0, 0, 0))
            screen.blit(level, (card.right - 60, card.top + 7))
            #exp
            exp_text = self.font_tiny.render(
                f"EXP: {monster.get('exp', 0)}/{10 + (monster['level'] - 1) * 5}",
                True,
                (0, 0, 0)
            )
            screen.blit(exp_text, (card.left + 80, card.top + 22))
            #max hp
            hp_bg = pg.Rect(card.left + 85, card.top + 45, 130, 10)
            pg.draw.rect(screen, (0, 0, 0), hp_bg, 2)
            #hp 
            hp_ratio = monster["hp"] / monster["max_hp"]
            hp_fill = pg.Rect(hp_bg.left, hp_bg.top, int(130 * hp_ratio), 10)
            pg.draw.rect(screen, (50, 200, 50), hp_fill)
            pg.draw.rect(screen, (0, 0, 0), hp_fill, 2)
            #hp text
            hp_text = self.font_small.render(f"{monster['hp']}/{monster['max_hp']}", True, (0, 0, 0))
            screen.blit(
                hp_text,
                (
                    hp_bg.centerx - hp_text.get_width() // 2,  
                    hp_bg.top - hp_text.get_height()        
                )
            )

            y_offset += 65

        #item (scrollable)
        item_area = pg.Rect(panel_x + 285, panel_y + 90, 230, 360)
        item_surface = pg.Surface((item_area.width, item_area.height), pg.SRCALPHA)
        #item list long/heigth
        total_height = len(self._items_data) * 45
        #scrollable space (total height - display)
        self.max_scroll = min(0, item_area.height - total_height)

        y = self.scroll
        for item in self._items_data:
            icon = Sprite(item["sprite_path"],(30, 30))
            icon.update_pos(Position(10, y))
            icon.draw(item_surface)
            

            name = self.font_small.render(item["name"], True, (0, 0, 0))
            item_surface.blit(name, (60, y + 10))

            amount = self.font_small.render(str(item["count"]), True, (0, 0, 0))
            rect = amount.get_rect()
            rect.right = item_area.width - 10
            rect.top = y + 10
            item_surface.blit(amount, rect)

            y += 45

        screen.blit(item_surface, item_area.topleft)
        

    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": list(self._monsters_data),
            "items": list(self._items_data)
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        items = data.get("items") or []
        bag = cls(monsters, items)
        return bag