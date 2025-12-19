import pygame as pg
import copy
from src.scenes.scene import Scene
from src.core.services import scene_manager, input_manager,sound_manager
from src.utils import GameSettings,Position
from src.utils.definition import Monster
from src.sprites import Sprite,BackgroundSprite
from src.interface.components import Button


TYPE_EFFECT = {
    "Fire":   {"Grass": 2.0, "Water": 0.5, "Fire": 1.0},
    "Water":  {"Fire": 2.0,  "Grass": 0.5, "Water": 1.0},
    "Grass":  {"Water": 2.0, "Fire": 0.5, "Grass": 1.0},
}

EVOLUTIONS = {
    "Bushyy": {
        5: {
            "name": "Bushyy+",
            "sprite": "menu_sprites/menusprite2.png",
            "stat_bonus": {"max_hp": 6, "atk": 2, "def": 2}
        },
        10: {
            "name": "Bushyy++",
            "sprite": "menu_sprites/menusprite3.png",
            "stat_bonus": {"max_hp": 8, "atk": 3, "def": 3}
        }
    },
    "Cheetos": {
        5: {
            "name": "Cheetos+",
            "sprite": "menu_sprites/menusprite8.png",
            "stat_bonus": {"max_hp": 5, "atk": 3, "def": 1}
        },
        10: {
            "name": "Cheetos++",
            "sprite": "menu_sprites/menusprite9.png",
            "stat_bonus": {"max_hp": 7, "atk": 4, "def": 2}
        }
    },
    "Seafish": {
        5: {
            "name": "Seafish+",
            "sprite": "menu_sprites/menusprite13.png",
            "stat_bonus": {"max_hp": 8, "atk": 2, "def": 3}
        },
        10: {
            "name": "Seafish++",
            "sprite": "menu_sprites/menusprite14.png",
            "stat_bonus": {"max_hp": 9, "atk": 3, "def": 4}
        }
    },
    "Mossfly": {
        5: {
            "name": "Mossfly+",
            "sprite": "menu_sprites/menusprite16.png",
            "stat_bonus": {"max_hp": 6, "atk": 3, "def": 2}
        }
    }
}

def load_battle_sprites(sheet,part):
    w, h = sheet.get_size()
    half = w // 2
    if(part == "left"):
        img = sheet.subsurface(pg.Rect(0, 0, half, h))     # left half
    if(part =="right"):
        img = sheet.subsurface(pg.Rect(half, 0, half, h)) # right half

    return img

def exp_needed(level: int) -> int:
    return 10 + (level - 1) * 5

class BattleScene(Scene):

    def __init__(self):
        super().__init__()
        self.gm = None
        self.enemy_data = None
        self.ready = False
        self.attack_cooldown = 0.1
        self.enemy_should_attack = False
        self.hp_animate_speed = 80 
        self.message_box_text = None
        self.waiting_for_click = False
        self.battle_over = False
        self.battle_result_text = None

        #animation atk
        self.attack_anims = {}  # "Fire": [frames], "Water": [frames], ...
        self.attack_anim_index = 0
        self.attack_anim_time = 0
        self.attack_anim_playing = False
        self.attack_anim_target = None
        self.attack_anim_frames = None 
        self.element_icons = {
            "Fire": "element/fire.png",
            "Water": "element/water.png",
            "Grass": "element/grass.png",
            "Normal": "element/normal.png"
        }
        self.potion_sprites = {
            "heal": Sprite("ingame_ui/heal.png", (30, 30)),
            "strength": Sprite("ingame_ui/strength.png", (30, 30)),
            "defense": Sprite("ingame_ui/defense.png", (30, 30)),
        }

        #item overlay
        self.show_item_menu = False
        # Keep original stats so buffs disappear after battle
        self.original_atk = 0
        self.original_def = 0
                        
    def calculate_damage(self, attacker, defender):
        atk = attacker["atk"]
        defense = defender["def"]
        
        base = max(1, atk - defense // 2)   # simple formula

        # Type effectiveness
        a_type = attacker.get("type", "Normal")
        d_type = defender.get("type", "Normal")

        multiplier = TYPE_EFFECT.get(a_type, {}).get(d_type, 1.0)

        dmg = int(base * multiplier)
        return max(1, dmg), multiplier    

    # Called FROM GameScene to start the battle
    def start_battle(self, game_manager):
        self.gm = game_manager
        
        self.enemy_data ={
        "name": "Mossfly",
        "type": "Grass",
        "hp": 40,
        "max_hp": 40,
        "level": 1,
        "exp": 0,   
        "atk": 10,
        "def": 10,
        "sprite_path": "menu_sprites/menusprite15.png"
      }
        if not self._setup():
            return
        self._setup()
        self.ready = True
        

    def _handle_hp(self,dt):
        if(self.enemy_display_hp > self.enemy_data["hp"]):
            self.enemy_display_hp -= self.hp_animate_speed * dt
            if(self.enemy_display_hp < self.enemy_data["hp"]):
                self.enemy_display_hp = self.enemy_data["hp"]
        if(self.player_display_hp > self.player_pokemon["hp"]):
            self.player_display_hp -= self.hp_animate_speed *dt
            if(self.player_display_hp < self.player_pokemon["hp"]):
                self.player_display_hp = self.player_pokemon["hp"]

    def _get_player_pokemon(self):
        for p in self.gm.bag._monsters_data:
            if p["hp"] > 0:
                return p
        return None
    def _setup(self):
        normal_btn = "UI/raw/UI_Flat_Button02a_3.png"
        hover_btn  = "UI/raw/UI_Flat_Button02a_2.png"

        self.attack_button = Button(
            img_path=normal_btn,
            img_hovered_path=hover_btn,
            x=50,
            y=GameSettings.SCREEN_HEIGHT - 120,
            width=180,
            height=60,
            on_click=self._attack
        )
        self.item_button = Button(
            img_path=normal_btn,
            img_hovered_path=hover_btn,
            x=300,    # between attack and run
            y=GameSettings.SCREEN_HEIGHT - 120,
            width=180,
            height=60,
            on_click=self._open_item_menu
        )
        self.run_button = Button(
            img_path=normal_btn,
            img_hovered_path=hover_btn,
            x=550,
            y=GameSettings.SCREEN_HEIGHT - 120,
            width=180,
            height=60,
            on_click=self._run_away
        )
        # pick first alive Pokémon
        self.player_pokemon = self._get_player_pokemon()
        if self.player_pokemon ==  None :
            print("No Pokémon available!")
            scene_manager.change_scene("game")
            return False
        self.enemy_display_hp = self.enemy_data["hp"]
        self.player_display_hp = self.player_pokemon["hp"]
        enemy_path =  self.enemy_data["sprite_path"]
        enemy_path = enemy_path.replace("menu_sprites/menusprite","sprites/sprite")
        self.enemy_sprite = Sprite(enemy_path)
        player_path = self.player_pokemon["sprite_path"]
        player_path = player_path.replace("menu_sprites/menusprite","sprites/sprite")
        self.player_sprite = Sprite(player_path)
        enemy_img = load_battle_sprites(self.enemy_sprite.image, "left")
        player_img = load_battle_sprites(self.player_sprite.image,"right")
        self.enemy_sprite.image = pg.transform.scale(enemy_img, (300, 300))
        self.enemy_sprite.rect.topleft = (810, 80)
        self.player_sprite.image = pg.transform.scale(player_img, (300, 300))
        self.player_sprite.rect.topleft =  (280, 230)

        #base atk and def for item buff
        self.original_atk = int(self.player_pokemon["atk"])
        self.original_def = int(self.player_pokemon["def"])

        self.bg = BackgroundSprite("backgrounds/background1.png")
        self.bg.image = pg.transform.scale(self.bg.image, (1280,530))
        self.font = pg.font.Font(None, 28)
        self.message_box_text = None
        self.waiting_for_click = False
        self.battle_over = False
        self.battle_result_text = None
        self.enemy_should_attack = False
        self.attack_anim_playing = False
        

        #animation
        def load_attack_anim(path):
            sheet = Sprite(path)
            frame_w = sheet.image.get_width() // 4
            frame_h = sheet.image.get_height()
            frames = []
            for i in range(4):
                frame = sheet.image.subsurface(pg.Rect(i * frame_w, 0, frame_w, frame_h))
                frame = pg.transform.scale(frame, (250, 250))
                frames.append(frame)
            return frames
        self.attack_anims["Fire"] = load_attack_anim("attack/attack5.png")
        self.attack_anims["Water"] = load_attack_anim("attack/attack3.png")
        self.attack_anims["Grass"] = load_attack_anim("attack/attack6.png")
        self.attack_anims["Normal"] = load_attack_anim("attack/attack7.png")
        return True
        
    def enter(self):
        sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")
        if(GameSettings.AUDIO_MUTED):
            sound_manager.pause_all()
        pass

    def play_attack_anim(self, attacker_type, target):
        self.attack_anim_frames = self.attack_anims.get(attacker_type, None)
        
        if not self.attack_anim_frames:
            return  # no animation

        self.attack_anim_playing = True
        self.attack_anim_index = 0
        self.attack_anim_time = 0
        self.attack_anim_target = target  # "enemy" or "player"

    def update(self, dt):
        if self.ready:
            self._handle_hp(dt)
        
        #animation atk
        if self.attack_anim_playing:
            self.attack_anim_time += dt
            if self.attack_anim_time > 0.07:
                self.attack_anim_time = 0
                self.attack_anim_index += 1

                if self.attack_anim_index >= len(self.attack_anim_frames):
                    self.attack_anim_playing = False

        if self.waiting_for_click:
            if input_manager.mouse_pressed(pg.BUTTON_LEFT):
                mx, my = pg.mouse.get_pos()
                
                # Click inside menu (0,530,1280,190)
                if 530 <= my <= 720:
                    if self.battle_over:
                        self.player_pokemon["atk"] = self.original_atk
                        self.player_pokemon["def"] = self.original_def
                        # End battle entirely
                        scene_manager.change_scene("game")
                        return
                    self.message_box_text = None
                    self.waiting_for_click = False
                    self.attack_cooldown = 0.1
                    
            return
        if not self.ready:
            return
        
        mx, my = pg.mouse.get_pos()

        if self.enemy_should_attack==False:
            if not self.show_item_menu:
                self.attack_button.update(dt)
                self.run_button.update(dt)
                if input_manager.key_pressed(pg.K_ESCAPE):
                    self._run_away()
            self.item_button.update(dt)
            
            if self.show_item_menu:
                menu_x, menu_y, menu_w, menu_h = 240, 450, 300, 150
                ROW_HEIGHT = 40
                
                # Define item click handlers and their vertical start positions (must match draw logic)
                item_rows_logic = [
                    (self._use_heal, menu_y + 5),
                    (self._use_strength, menu_y + 55),
                    (self._use_defense, menu_y + 105),
                ]

                if input_manager.mouse_pressed(pg.BUTTON_LEFT):
                    clicked_on_item = False
                    for i, (click_handler, y_start) in enumerate(item_rows_logic):
                        # Calculate the row rectangle for collision check
                        row_rect = pg.Rect(menu_x, y_start, menu_w, ROW_HEIGHT)
                        
                        if row_rect.collidepoint(mx, my):
                            click_handler()
                            clicked_on_item = True
                            break
                    
                    if not clicked_on_item:
                        # If clicked inside the main menu box but not on an item, close the menu
                        menu_rect = pg.Rect(menu_x, menu_y, menu_w, menu_h)
                        if menu_rect.collidepoint(mx, my):
                            self.show_item_menu = False
            
        if self.enemy_should_attack and self.waiting_for_click == False:
            self.attack_cooldown -=dt
            if self.attack_cooldown <= 0:
                if input_manager.mouse_pressed(pg.BUTTON_LEFT) and pg.Rect(0,530,1280,190).collidepoint(mx,my):
                    print("enemy atk")
                    self._enemy_attack()

    def _attack(self):
        if self.show_item_menu:
            self.show_item_menu = False
        dmg, mult = self.calculate_damage(self.player_pokemon, self.enemy_data)
        self.enemy_data["hp"] -= dmg
        self.enemy_data["hp"] = max(0, self.enemy_data["hp"])
        #animation
        atk_type = self.player_pokemon["type"]
        self.play_attack_anim(atk_type, "enemy")
        #text
        print(f"Player dealt {dmg} damage! (x{mult} effectiveness)")
        self.message_box_text = (
            f"{self.player_pokemon['name']} dealt {dmg} damage! (x{mult} effectiveness)"
        )
        self.waiting_for_click = True
        self.enemy_should_attack = True

        if self.enemy_data["hp"] <= 0:
            self.player_pokemon["atk"] = self.original_atk
            self.player_pokemon["def"] = self.original_def  

            #coin gain
            for item in self.gm.bag._items_data:
                if item["name"] == "Coins":
                    item["count"] += 5 + self.enemy_data["level"] * 2
            # ===== EXP GAIN =====
            if "exp" not in self.player_pokemon:
                self.player_pokemon["exp"] = 0
            gained_exp = 10 + self.enemy_data["level"] * 5
            self.player_pokemon["exp"] += gained_exp
            leveled_up = False

            evolved = False
            while self.player_pokemon["exp"] >= exp_needed(self.player_pokemon["level"]):
                self.player_pokemon["exp"] -= exp_needed(self.player_pokemon["level"])
                self.player_pokemon["level"] += 1

                # base level-up stats
                self.player_pokemon["max_hp"] += 5
                self.player_pokemon["atk"] += 2
                self.player_pokemon["def"] += 1
                self.player_pokemon["hp"] = self.player_pokemon["max_hp"]
                self.player_display_hp = self.player_pokemon["hp"]

                # evolution check
                if self.try_evolution(self.player_pokemon):
                    self.player_display_hp = self.player_pokemon["hp"]
                    #NEW SPRITE
                    player_path = self.player_pokemon["sprite_path"]
                    player_path = player_path.replace("menu_sprites/menusprite","sprites/sprite")
                    self.player_sprite = Sprite(player_path)
                    player_img = load_battle_sprites(self.player_sprite.image,"right")
                    self.player_sprite.image = pg.transform.scale(player_img, (300, 300))
                    self.player_sprite.rect.topleft =  (280, 230)
                    evolved = True

                leveled_up = True
            self.original_atk = self.player_pokemon["atk"]
            self.original_def = self.player_pokemon["def"]
            if evolved:
                self.message_box_text = f"You win! +{gained_exp} EXP. Evolution!"
            elif leveled_up:
                self.message_box_text = f"You win! +{gained_exp} EXP. Level up!"
            else:
                self.message_box_text = f"You win! +{gained_exp} EXP."
            self.battle_over = True
            self.waiting_for_click = True
            return
        
    def _run_away(self):
        self.show_item_menu = False
        self.player_pokemon["atk"] = self.original_atk
        self.player_pokemon["def"] = self.original_def
        scene_manager.change_scene("game")
        
    def _open_item_menu(self):
        if self.waiting_for_click or self.enemy_should_attack:
            return
        self.show_item_menu = not self.show_item_menu

    #potion amount
    def get_item_count(self, item_name):
        for item in self.gm.bag._items_data:
            if item["name"] == item_name:
                return item["count"]
        return 0
    
    #evolution check
    def try_evolution(self, monster: dict) -> bool:
        name = monster["name"]
        level = monster["level"]

        if name not in EVOLUTIONS:
            return False

        evo_data = EVOLUTIONS[name].get(level)
        if not evo_data:
            return False

        # Apply evolution
        monster["name"] = evo_data["name"]
        monster["sprite_path"] = evo_data["sprite"]

        bonus = evo_data["stat_bonus"]
        monster["max_hp"] += bonus["max_hp"]
        monster["atk"] += bonus["atk"]
        monster["def"] += bonus["def"]
        monster["hp"] = monster["max_hp"]

        return True

    def _use_heal(self):
        # Check bag count
        for item in self.gm.bag._items_data:
            if item["name"] == "Heal Potion":
                if item["count"] <= 0:
                    self.message_box_text = "No Heal Potions left!"
                    self.waiting_for_click = True
                    return
                item["count"] -= 1  # remove from bag
                break

        self.show_item_menu = False
        self.player_pokemon["hp"] = min(
            self.player_pokemon["hp"] + 20,
            self.player_pokemon["max_hp"]
        )
        self.player_display_hp = self.player_pokemon["hp"]
        self.message_box_text = f"{self.player_pokemon['name']} healed 20 HP!"
        self.waiting_for_click = True
        self.enemy_should_attack = True


    def _use_strength(self):
        for item in self.gm.bag._items_data:
            if item["name"] == "Strength Potion":
                if item["count"] <= 0:
                    self.message_box_text = "No Strength Potions left!"
                    self.waiting_for_click = True
                    return
                item["count"] -= 1
                break

        self.show_item_menu = False
        self.player_pokemon["atk"] += int(self.original_atk * 0.5)
        self.message_box_text = f"{self.player_pokemon['name']}'s ATK rose!"
        self.waiting_for_click = True
        self.enemy_should_attack = True



    def _use_defense(self):
        for item in self.gm.bag._items_data:
            if item["name"] == "Defense Potion":
                if item["count"] <= 0:
                    self.message_box_text = "No Defense Potions left!"
                    self.waiting_for_click = True
                    return
                item["count"] -= 1
                break

        self.show_item_menu = False
        self.player_pokemon["def"] += int(self.original_def * 0.5)
        self.message_box_text = f"{self.player_pokemon['name']}'s DEF rose!"
        self.waiting_for_click = True
        self.enemy_should_attack = True


        
    def _enemy_attack(self):
        # enemy hits back
        self.attack_cooldown = 0
        self.enemy_should_attack = False
        dmg, mult = self.calculate_damage(self.enemy_data, self.player_pokemon)
        self.player_pokemon["hp"] -= dmg
        self.player_pokemon["hp"] =  max(0,self.player_pokemon["hp"])
        #animation
        atk_type = self.enemy_data["type"]  
        self.play_attack_anim(atk_type, "player")
        #dmg message
        self.message_box_text = (
            f"{self.enemy_data['name']} dealt {dmg} damage! (x{mult} effectiveness)"
        )
        self.waiting_for_click = True

        print(f"Enemy dealt {dmg} damage! (x{mult} effectiveness)")

        if self.player_pokemon["hp"] <= 0:
            self.player_pokemon["atk"] = self.original_atk
            self.player_pokemon["def"] = self.original_def
            new_p = self._get_player_pokemon()
            if new_p:
                self.player_pokemon = new_p
                self.player_display_hp = new_p["hp"]
                
                player_path = self.player_pokemon["sprite_path"]
                player_path = player_path.replace("menu_sprites/menusprite","sprites/sprite")
                self.player_sprite = Sprite(player_path)
                player_img = load_battle_sprites(self.player_sprite.image,"right")
                self.player_sprite.image = pg.transform.scale(player_img, (300, 300))
                self.player_sprite.rect.topleft =  (280, 230)
                #base atk and def for item buff
                self.original_atk = int(self.player_pokemon["atk"])
                self.original_def = int(self.player_pokemon["def"])

            else:
                self.message_box_text = "You lose!"
                self.battle_over = True
                self.waiting_for_click = True

    def _draw_hp(self, s, x, y, hp, maxhp):
        ratio = hp / maxhp
        pg.draw.rect(s, (0, 0, 0), (x, y, 150, 12))
        pg.draw.rect(s, (40, 200, 40), (x+1, y+1, int(148 * ratio), 10))

    def _draw_button_text(self, screen, button: Button, text: str):
        txt_surf = self.font.render(text, True, (0, 0, 0))
        # detect hover using the button's current image reference
        is_hover = (button.img_button is button.img_button_hover)
        y_offset = 5 if is_hover else 0   # drop 5px when hovered
        x = button.hitbox.centerx - txt_surf.get_width() // 2
        y = button.hitbox.centery - txt_surf.get_height() // 2 + y_offset
        screen.blit(txt_surf, (x, y))

    def _draw_element_icon(self, screen, type_name, x, y):
        icon_path = self.element_icons.get(type_name, None)
        if not icon_path:
            return
        elem_icon = Sprite(icon_path, (22, 22))
        elem_icon.update_pos(Position(x, y))
        elem_icon.draw(screen)

    def draw(self, screen):
        self.font_small = pg.font.Font(None, 22)
        if not self.ready:
            return

        self.bg.draw(screen)

        # enemy monster
        self.enemy_sprite.draw(screen)
        #enemy card
        e_card = pg.Rect(850, 350, 230, 50)
        pg.draw.rect(screen, (255, 255, 255), e_card, border_radius=10)
        pg.draw.rect(screen, (0, 0, 0), e_card, 2, border_radius=10)
        #enemy monster icon
        e_sprite = Sprite("ingame_ui/" + self.enemy_data["sprite_path"],(45, 45))
        e_sprite .rect.topleft = (e_card.left + 15, e_card.centery - 26)
        e_sprite.draw(screen)
        #enemy element
        self._draw_element_icon(screen,self.enemy_data.get("type", "Normal"),e_card.right - 30,e_card.top + 5)
        #enemy name
        e_name = self.font_small.render(self.enemy_data["name"], True, (0, 0, 0))
        screen.blit(e_name, (e_card.left + 80, e_card.top + 7))
        #enemy level
        e_level = self.font_small.render(f"Lv.{self.enemy_data['level']}", True, (0, 0, 0))
        screen.blit(e_level, (e_card.right - 60, e_card.top + 7))
        #enemy max hp
        e_hp_bg = pg.Rect(e_card.left + 80, e_card.top + 35, 130, 10)
        pg.draw.rect(screen, (0, 0, 0), e_hp_bg, 2)
        #enemy hp 
        e_hp_ratio = self.enemy_display_hp / self.enemy_data["max_hp"]
        e_hp_fill = pg.Rect(e_hp_bg.left, e_hp_bg.top, int(130 * e_hp_ratio), 10)
        pg.draw.rect(screen, (50, 200, 50), e_hp_fill)
        pg.draw.rect(screen, (0, 0, 0), e_hp_fill, 2)
        #enemy hp text
        e_hp_text = self.font_small.render(f"{self.enemy_data['hp']}/{self.enemy_data['max_hp']}", True, (0, 0, 0))
        screen.blit(
            e_hp_text,
            (
                e_hp_bg.centerx - e_hp_text.get_width() // 2,  
                e_hp_bg.top - e_hp_text.get_height()        
            )
        )


        # player monster 
        self.player_sprite.draw(screen)
        #player card
        p_card = pg.Rect(30, 460, 230, 50)
        pg.draw.rect(screen, (255, 255, 255), p_card, border_radius=10)
        pg.draw.rect(screen, (0, 0, 0), p_card, 2, border_radius=10)
        #player monster icon
        p_sprite = Sprite("ingame_ui/" + self.player_pokemon["sprite_path"],(45, 45))
        p_sprite.rect.topleft = (p_card.left + 15, p_card.centery - 26)
        p_sprite.draw(screen)
        #player element
        self._draw_element_icon(screen,self.player_pokemon.get("type", "Normal"),p_card.right - 30,p_card.top + 5)
        #player name
        p_name = self.font_small.render(self.player_pokemon["name"], True, (0, 0, 0))
        screen.blit(p_name, (p_card.left + 80, p_card.top + 7))
        #player level
        p_level = self.font_small.render(f"Lv.{self.player_pokemon['level']}", True, (0, 0, 0))
        screen.blit(p_level, (p_card.right - 60, p_card.top + 7))
        #player max hp
        p_hp_bg = pg.Rect(p_card.left + 80, p_card.top + 35, 130, 10)
        pg.draw.rect(screen, (0, 0, 0), p_hp_bg, 2)
        #player hp 
        p_hp_ratio = self.player_display_hp / self.player_pokemon["max_hp"]
        p_hp_fill = pg.Rect(p_hp_bg.left, p_hp_bg.top, int(130 * p_hp_ratio), 10)
        pg.draw.rect(screen, (50, 200, 50), p_hp_fill)
        pg.draw.rect(screen, (0, 0, 0), p_hp_fill, 2)
        #player hp text
        p_hp_text = self.font_small.render(f"{self.player_pokemon['hp']}/{self.player_pokemon['max_hp']}", True, (0, 0, 0))
        screen.blit(
            p_hp_text,
            (
                p_hp_bg.centerx - p_hp_text.get_width() // 2,  
                p_hp_bg.top - p_hp_text.get_height()        
            )
        )
        #animation atk
        if self.attack_anim_playing:
            frame = self.attack_anim_frames[self.attack_anim_index]

            if self.attack_anim_target == "enemy":
                pos = (
                    self.enemy_sprite.rect.centerx - 70,
                    self.enemy_sprite.rect.centery - 75
                )
            else:
                pos = (
                    self.player_sprite.rect.centerx - 70,
                    self.player_sprite.rect.centery - 75
                )

            screen.blit(frame, pos)
        #menu
        pg.draw.rect(screen, (0, 0, 0), (0,530,1280,190))
        pg.draw.rect(screen, (255, 255, 255), (0,530,1280,190),2)
        if not self.message_box_text and not self.enemy_should_attack:
            self.attack_button.draw(screen)
            self.item_button.draw(screen)
            self.run_button.draw(screen)
            self._draw_button_text(screen, self.attack_button, "ATTACK")
            self._draw_button_text(screen, self.item_button, "ITEM") 
            self._draw_button_text(screen, self.run_button, "RUN")
        if self.enemy_should_attack and self.waiting_for_click == False:
            txt = self.font.render("ENEMY TURN", True, (255, 255, 255))
            screen.blit(txt, (640 - txt.get_width()//2,
                            GameSettings.SCREEN_HEIGHT - 120))
            
        #item overlay
        if self.show_item_menu:
            menu_x, menu_y, menu_w, menu_h = 240, 450, 300, 150
            ROW_HEIGHT = 40
            
            # Draw main menu box background and border
            pg.draw.rect(screen, (255, 165, 0), (menu_x, menu_y, menu_w, menu_h))
            pg.draw.rect(screen, (255, 255, 255), (menu_x, menu_y, menu_w, menu_h), 2)

            # Draw definitions for the rows
            item_rows_draw = [
                ("Heal Potion", "heal", "Heal Potion", menu_y + 5),
                ("Strength Potion", "strength", "Strength Potion", menu_y + 55),
                ("Defense Potion", "defense", "Defense Potion", menu_y + 105),
            ]
            
            for display_name, key, data_name, y_start in item_rows_draw:
                row_rect = pg.Rect(menu_x, y_start, menu_w, ROW_HEIGHT)
                mx, my = pg.mouse.get_pos()

                if row_rect.collidepoint(mx, my):
                    pg.draw.rect(screen, (255, 255, 255), row_rect.inflate(-3, -3), border_radius=5)

                # Icon
                sprite = self.potion_sprites.get(key)
                if sprite:
                    sprite_x = menu_x + 10
                    sprite_y = row_rect.centery - sprite.image.get_height() // 2
                    sprite.update_pos(Position(sprite_x, sprite_y))
                    sprite.draw(screen)

                # Text
                count = self.get_item_count(data_name)
                txt_surf = self.font.render(f"{display_name}  (x{count})", True, (0, 0, 0))
                screen.blit(txt_surf, (menu_x + 60, row_rect.centery - txt_surf.get_height() // 2))

        if self.message_box_text:
            txt = self.font.render(self.message_box_text, True, (255, 255, 255))
            screen.blit(txt, (640 - txt.get_width()//2, 615-txt.get_height()//2))   # Position inside battle menu
           