import pygame as pg
import json
from src.utils import GameSettings,Position
from src.sprites import Sprite
from src.interface.components import Button
from src.core.services import input_manager

class PCBox:
    def __init__(self, monsters: list[dict] | None = None):
        self.monsters = monsters if monsters is not None else []
        
        self.visible = False
        self.gm = None
        
        self.font_title = pg.font.Font(None, 50)
        self.font_small = pg.font.Font(None, 22)

        self.selected_sourc= None
        self.selected_index= None

        self.panel_width = 900
        self.panel_height = 600

        self.grid_cols = 6
        self.grid_rows = 5
        self.slot_size = 75
        self.slot_margin = 6
        self.pc_slot_rects= []

        self._build_layout()

    def to_dict(self) -> list[dict]:
        return self.monsters

    @classmethod
    def from_dict(cls, data: list[dict]):
        return cls(monsters=data)

    def add(self, mon: dict):
        self.monsters.append(mon)

    def remove(self, index: int) -> dict | None:
        if 0 <= index < len(self.monsters):
            return self.monsters.pop(index)
        return None
    
    def open(self, gm):
        
        self.gm = gm
        self.visible = True
        self.selected_source = None
        self.selected_index = None

    def close(self):
        self.visible = False
        self.selected_source = None
        self.selected_index = None
    
    def _build_layout(self):
        sw, sh = GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT
        panel_x = (sw - self.panel_width) // 2
        panel_y = (sh - self.panel_height) // 2

        # Party area 
        party_x = panel_x + 50
        party_y = panel_y + 100
        party_height = 56
        spacing = 12

        self.party_slot_rects = []
        for i in range(6):  # max 6 party mons
            rect = pg.Rect(party_x, party_y + i * (party_height + spacing), 260, party_height)
            self.party_slot_rects.append(rect)

        # PC grid 
        grid_start_x = panel_x + 355
        grid_start_y = panel_y + 100

        self.pc_slot_rects = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = grid_start_x + col * (self.slot_size + self.slot_margin)
                y = grid_start_y + row * (self.slot_size + self.slot_margin)
                self.pc_slot_rects.append(pg.Rect(x, y, self.slot_size, self.slot_size))

        # buttons on bottom
        btn_y = panel_y + self.panel_height - 65
        self.btn_withdraw_rect = pg.Rect(450, btn_y, 140, 40)
        self.btn_deposit_rect = pg.Rect(690, btn_y, 140, 40)

        # Close button
        self.close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            panel_x + self.panel_width - 58,
            panel_y + 15,
            40, 40,
            self.toggle
        )
    def toggle(self):
        self.visible = False
    def update(self, dt: float):
        if not self.visible :
            return

        mx, my = pg.mouse.get_pos()
        #close button
        self.close_button.update(dt)
        # close with ESC
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return

        if input_manager.mouse_pressed(pg.BUTTON_LEFT):

            if self.btn_withdraw_rect and self.btn_withdraw_rect.collidepoint(mx, my):
                self._handle_withdraw()
                return

            if self.btn_deposit_rect and self.btn_deposit_rect.collidepoint(mx, my):
                self._handle_deposit()
                return

            # click PC grid
            for i, rect in enumerate(self.pc_slot_rects):
                if rect.collidepoint(mx, my):
                    if i < len(self.monsters):
                        self.selected_source = "pc"
                        self.selected_index = i
                    else:
                        self.selected_source = None
                        self.selected_index = None
                    return

            # click party list
            party_list = self.gm.bag._monsters_data if self.gm and self.gm.bag else []
            for i, rect in enumerate(self.party_slot_rects):
                if rect.collidepoint(mx, my):
                    if i < len(party_list):
                        self.selected_source = "party"
                        self.selected_index = i
                    else:
                        self.selected_source = None
                        self.selected_index = None
                    return

            # clicked elsewhere
            self.selected_source = None
            self.selected_index = None

    def _handle_withdraw(self):
        #pc->party
        if self.selected_source != "pc" or self.selected_index is None:
            return
        if self.gm is None:
            return

        party = self.gm.bag._monsters_data

        # party full
        if len(party) >= 6:
            print("Party full! Cannot withdraw.")
            return

        if not (0 <= self.selected_index < len(self.monsters)):
            return

        mon = self.remove(self.selected_index)
        if mon:
            party.append(mon)

        self.selected_source = None
        self.selected_index = None

    def _handle_deposit(self):
        #party->pc
        if self.selected_source != "party" or self.selected_index is None:
            return
        if self.gm is None:
            return

        party = self.gm.bag._monsters_data

        if not (0 <= self.selected_index < len(party)):
            return

        # minumum has 1 pokemon in bag
        if len(party) <= 1:
            print("You cannot deposit your last Pokémon!")
            return

        mon = party.pop(self.selected_index)
        self.add(mon)

        self.selected_source = None
        self.selected_index = None

    def draw(self, screen: pg.Surface):
        if not self.visible :
            return

        sw, sh = GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT
        panel_x = (sw - self.panel_width) // 2
        panel_y = (sh - self.panel_height) // 2
        panel_rect = pg.Rect(panel_x, panel_y, self.panel_width, self.panel_height)
        
        # dim background
        dim = pg.Surface((sw, sh), pg.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # panel background + border 
        pg.draw.rect(screen, (50, 50, 50), panel_rect.move(6, 6), border_radius=20)
        pg.draw.rect(screen, (255, 165, 0), panel_rect, border_radius=20)
        pg.draw.rect(screen, (0, 0, 0), panel_rect, 3, border_radius=20)

        #close button
        self.close_button.draw(screen)

        # title
        title = self.font_title.render("PC Box", True, (0, 0, 0))
        screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 25))

        # label party
        label_party = self.font_small.render("Party", True, (0, 0, 0))
        screen.blit(label_party, (panel_x + 60, panel_y + 75))
        # label box
        label_box = self.font_small.render("Box", True, (0, 0, 0))
        screen.blit(label_box, (panel_x + 355, panel_y + 75))

        # draw party list
        party_list = self.gm.bag._monsters_data if self.gm and self.gm.bag else []
        for i, rect in enumerate(self.party_slot_rects):
            border_color = (0, 0, 0)
            if self.selected_source == "party" and self.selected_index == i:
                border_color = (255,0, 0)

            pg.draw.rect(screen, (255, 255, 255), rect, border_radius=10)
            pg.draw.rect(screen, border_color, rect, 2, border_radius=10)

            if i < len(party_list):
                mon = party_list[i]

                # sprite
                try:
                    sprite = Sprite("ingame_ui/" + mon["sprite_path"],(45, 45))
                    sprite.update_pos(Position(rect.left + 8, rect.top + 5))
                    sprite.draw(screen)
                    
                except Exception:
                    pass

                # name
                name = self.font_small.render(mon["name"], True, (0, 0, 0))
                screen.blit(name, (rect.left + 65, rect.top + 10))

                # level
                level = self.font_small.render(f"Lv.{mon['level']}", True, (0, 0, 0))
                screen.blit(level, (rect.left + 65, rect.top + 30))

        # draw PC grid
        for i, rect in enumerate(self.pc_slot_rects):
            border_color = (0, 0, 0)
            if self.selected_source == "pc" and self.selected_index == i:
                border_color = (255, 0, 0)

            pg.draw.rect(screen, (255, 255, 255), rect, border_radius=8)
            pg.draw.rect(screen, border_color, rect, 2, border_radius=8)

            if i < len(self.monsters):
                mon = self.monsters[i]
                try:
                    sprite = Sprite("ingame_ui/" + mon["sprite_path"],(60, 60))
                    sprite.rect.center = rect.center
                    sprite.draw(screen)
                    
                except Exception:
                    pass

        # withdraw button
        pg.draw.rect(screen, (255, 255, 255), self.btn_withdraw_rect, border_radius=10)
        pg.draw.rect(screen, (0, 0, 0), self.btn_withdraw_rect, 2, border_radius=10)
        label = self.font_small.render("Withdraw", True, (0, 0, 0))
        screen.blit(
            label,
            (
                self.btn_withdraw_rect.centerx - label.get_width() // 2,
                self.btn_withdraw_rect.centery - label.get_height() // 2
            ))
        #deposit button
        pg.draw.rect(screen, (255, 255, 255), self.btn_deposit_rect, border_radius=10)
        pg.draw.rect(screen, (0, 0, 0), self.btn_deposit_rect, 2, border_radius=10)
        label = self.font_small.render("Deposit", True, (0, 0, 0))
        screen.blit(
            label,
            (
                self.btn_deposit_rect.centerx - label.get_width() // 2,
                self.btn_deposit_rect.centery - label.get_height() // 2
            ))
        