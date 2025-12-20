import pygame as pg
import threading
import time

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.core.services import scene_manager
from src.utils import Logger, PositionCamera, GameSettings, Position, Direction
from src.core.services import sound_manager, input_manager
from src.sprites import Sprite
from typing import override
from src.interface.components import Button
from src.interface.minimap import Minimap
from src.interface.components.chat_overlay import ChatOverlay

class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    
    def __init__(self):
        super().__init__()
        # Game Manager
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        
        # Online Manager
        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
            
            self.chat_overlay = ChatOverlay(
                send_callback=self.online_manager.send_chat,
                get_messages=self.online_manager.get_recent_chat    
            )

        else:
            self.online_manager = None
            self.chat_overlay = None
        self._chat_bubbles = {}          # { player_id : (text, expire_time) }
        self._last_chat_id_seen = 0      # last chat message ID seen
        self._chat_last_activity = time.monotonic()   # last time chat happened
        self._chat_visible = False                    # controls chatbox visibility
        #nav
        self.nav_overlay_open = False
        self.nav_map_buttons: list[tuple[str, Button]] = []
        self.nav_btn_normal = "UI/raw/UI_Flat_Button02a_3.png"
        self.nav_btn_hover = "UI/raw/UI_Flat_Button02a_2.png"
        self.nav_font = pg.font.Font(None, 28)
        self.nav_small_font = pg.font.Font(None, 24)

        self.cooldown = 0
        #nav button 
        self.nav_open_button = Button(
            self.nav_btn_normal,
            self.nav_btn_hover,
            GameSettings.SCREEN_WIDTH - 210, 20, 50, 50,
            self._toggle_nav_overlay
            )
        #settings button
        self.settings_button = Button(
            "UI/button_setting.png",
            "UI/button_setting_hover.png",
            GameSettings.SCREEN_WIDTH - 70, 20, 50, 50,
            self.toggle_settings
        )
        #bag button
        self.bag_button = Button(
            "UI/button_backpack.png",
            "UI/button_backpack_hover.png",
            GameSettings.SCREEN_WIDTH - 140, 20,   
            50, 50,
            lambda:self.game_manager.bag.toggle()
        )
        
        #save button
        self.save_button = Button(
            "UI/button_save.png",
            "UI/button_save_hover.png",
            GameSettings.SCREEN_WIDTH // 2 - 177,
            GameSettings.SCREEN_HEIGHT // 2 + 43,
            75,
            60,
            self.save_game
        )
        self.load_button = Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            GameSettings.SCREEN_WIDTH // 2 - 80,
            GameSettings.SCREEN_HEIGHT // 2 + 43,
            75,
            60,
            self.load_game
        )
        #back button
        self.show_settings = False
        self.back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            GameSettings.SCREEN_WIDTH // 2 + 170,
            GameSettings.SCREEN_HEIGHT // 2 + 130,
            80, 50,
            self.toggle_scene
        )
        #x button for settings
        self.x_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            GameSettings.SCREEN_WIDTH // 2 + 213,
            GameSettings.SCREEN_HEIGHT // 2 - 180,
            40, 40,
            self.toggle_settings,
        )
        self.volume = GameSettings.AUDIO_VOLUME
        self.muted = GameSettings.AUDIO_MUTED

         # Slider setup
         
        self.slider_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - 350) // 2,
            (GameSettings.SCREEN_HEIGHT // 2) - 70,
            350,
            10
        )
        self.slider_knob_rect = pg.Rect(0, 0, 20, 20)
        self._update_knob_pos()

        # Mute toggle
        self.toggle_rect = pg.Rect(self.slider_rect.left, self.slider_rect.bottom + 40, 80, 30)
        self.dragging = False
        self.show_bag = False
        self.item_scroll = 0
        self.item_scroll_speed = 20
        self.minimap = Minimap(self.game_manager.current_map, self.game_manager.player)



    def _update_knob_pos(self):
        self.slider_knob_rect.center = (
            self.slider_rect.left + int(self.volume * self.slider_rect.width),
            self.slider_rect.centery,
        )
    
    def toggle_mute(self):
        GameSettings.AUDIO_MUTED = not GameSettings.AUDIO_MUTED
        self.muted = GameSettings.AUDIO_MUTED
        if self.muted:
            sound_manager.pause_all()
        else:
            sound_manager.resume_all()

    def toggle_scene(self):
        self.show_settings = not self.show_settings
        scene_manager.change_scene("menu")
        

    def toggle_settings(self):
        self.show_settings = not self.show_settings

    def save_game (self):
        try:
            self.game_manager.save("saves/game0.json")
            print("[INFO] Game saved successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to save game: {e}")
    def load_game(self):
        try:
            new_manager = self.game_manager.load("saves/game0.json")
            if new_manager:
                self.game_manager = new_manager
                print("[INFO] Game loaded successfully.")
            else:
                print("[WARN] No save file found.")
        except Exception as e:
            print(f"[ERROR] Failed to load game: {e}")

    def _toggle_nav_overlay(self):
        if self.nav_overlay_open:
            self._close_nav_overlay()
        else:
            self._open_nav_overlay()

    def _open_nav_overlay(self):
        self.nav_overlay_open = True
        self._rebuild_nav_buttons()

    def _close_nav_overlay(self):
        self.nav_overlay_open = False
        self.nav_map_buttons = []

    def _on_click_map_destination(self, map_name: str):
        self._close_nav_overlay()
        if self.game_manager.player:
            # compute BFS to teleport that leads to map_name
            self.game_manager.player.start_navigation_to_map(map_name)

    def _rebuild_nav_buttons(self):
        # ONLY show destinations that current map can teleport to
        cur_map = self.game_manager.current_map
        if not cur_map:
            self.nav_map_buttons = []
            return

        # get unique destination names from current map teleports
        names = []
        seen = set()
        for tp in cur_map.teleporters:
            dest = tp.destination
            if dest == cur_map.path_name:
                continue
            if dest in seen:
                continue
            seen.add(dest)
            names.append(dest)

        # (optional) sort for stable order
        names.sort()

        panel_w, panel_h = 420, 360
        panel_x = (GameSettings.SCREEN_WIDTH - panel_w) // 2
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_h) // 2

        self.nav_map_buttons = []
        btn_w, btn_h = 160, 46
        gap = 14
        cols = 2

        start_x = panel_x + 40
        start_y = panel_y + 90

        for i, name in enumerate(names):
            r = i // cols
            c = i % cols
            x = start_x + c * (btn_w + gap)
            y = start_y + r * (btn_h + gap)

            btn = Button(
                self.nav_btn_normal,
                self.nav_btn_hover,
                x, y, btn_w, btn_h,
                lambda n=name: self._on_click_map_destination(n)
            )
            self.nav_map_buttons.append((name, btn))

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if(GameSettings.AUDIO_MUTED):
            sound_manager.pause_all()
        if self.online_manager:
            self.online_manager.enter()
        
    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()
        
    @override
    def update(self, dt: float):
        #navigation
        if not self.show_settings:
            self.nav_open_button.update(dt)
        if self.nav_overlay_open:
            # ESC closes overlay
            if input_manager.key_pressed(pg.K_ESCAPE):
                self._close_nav_overlay()
                return

            # update buttons so hover/click works
            for _, btn in self.nav_map_buttons:
                btn.update(dt)

            return
        
        #press b to open bag
        if(self.show_settings == False and self.game_manager.pc_box.visible == False and self.game_manager.current_shop_overlay == None and (not self.chat_overlay or not self.chat_overlay.is_open)):
            if input_manager.key_pressed(pg.K_b):
                    self.game_manager.bag.toggle()

        
        
        #press esc to open settings
        if(self.game_manager.bag.visible == False and self.game_manager.pc_box.visible == False and self.game_manager.current_shop_overlay == None and (not self.chat_overlay or not self.chat_overlay.is_open)):
            if input_manager.key_pressed(pg.K_ESCAPE):
                    self.toggle_settings()

        
        #if bag overlay open, dont update the rest 
        self.bag_button.update(dt)
        self.game_manager.bag.update(dt)

        #chat
        if self.chat_overlay:
            # Open chat: press ENTER
            if input_manager.key_pressed(pg.K_RETURN) and not self.chat_overlay.is_open:
                self.chat_overlay.open()
                self._chat_visible = True
                self._chat_last_activity = time.monotonic()
            # If chat is open → block movement update
            if self.chat_overlay.is_open:
                self.chat_overlay.update(dt)
                self._chat_last_activity = time.monotonic()
            
            if not self.chat_overlay.is_open:   # only auto-hide if not typing chat
                if time.monotonic() - self._chat_last_activity > 5:
                    self._chat_visible = False
                
                

        #show bag
        if(self.game_manager.bag.visible):
            return
        #shop
        if self.game_manager.current_shop_overlay:
            self.game_manager.current_shop_overlay.update(dt)
            return
        
        #pc_box
        if self.game_manager.pc_box.visible:
            self.game_manager.pc_box.update(dt)
            return
        # Update settng button
        self.settings_button.update(dt)
        
        #if setting overlay open, dont update the rest (only back button)
        if self.show_settings:
            self.volume = GameSettings.AUDIO_VOLUME
            self.muted = GameSettings.AUDIO_MUTED
            self._update_knob_pos()
            self.back_button.update(dt)
            self.x_button.update(dt)
            self.save_button.update(dt)
            self.load_button.update(dt)
            mouse_pressed = pg.mouse.get_pressed()[0]
            mouse_x, mouse_y = pg.mouse.get_pos()

            # Volume slider drag
            if mouse_pressed and self.slider_rect.collidepoint(mouse_x, mouse_y):
                self.dragging = True
            if not mouse_pressed:
                self.dragging = False

            if self.dragging:
                rel_x = mouse_x - self.slider_rect.left
                rel_x = max(0, min(self.slider_rect.width, rel_x))
                self.volume = rel_x / self.slider_rect.width
                GameSettings.AUDIO_VOLUME = self.volume
                
                if sound_manager.current_bgm :
                    sound_manager.current_bgm.set_volume(self.volume)
                self._update_knob_pos()

            # Mute toggle
            if input_manager.mouse_pressed(pg.BUTTON_LEFT):
                if self.toggle_rect.collidepoint(mouse_x, mouse_y):
                    self.toggle_mute()

            return
        # Check if there is assigned next scene
        self.game_manager.try_switch_map()
        
        # Update player and other data
        if not self.chat_overlay or not self.chat_overlay.is_open:
            if self.game_manager.player:
                self.game_manager.player.update(dt)
            for enemy in self.game_manager.current_enemy_trainers:
                enemy.update(dt)    
            self.cooldown -= dt

        #minimap
        self.minimap.update_map(self.game_manager.current_map)
        self.minimap.update_enemy_trainers(self.game_manager.current_enemy_trainers)

        
        #bush
        if self.game_manager.current_map.check_bush(self.game_manager.player.position):
            if(self.cooldown <=0):
                catch_scene = scene_manager.get_scene("catch")
                catch_scene.start_catch(self.game_manager)
                scene_manager.change_scene("catch")
                self.cooldown = 1
            
        
        
        if self.online_manager:
             try:
                 msgs = self.online_manager.get_recent_chat(50)
                 max_id = self._last_chat_id_seen
                 now = time.monotonic()
                 for m in msgs:
                     mid = int(m.get("id", 0))
                     if mid <= self._last_chat_id_seen:
                         continue
                     if mid > self._last_chat_id_seen:
                         self._chat_visible = True
                         self._chat_last_activity = now
                     sender = int(m.get("from", -1))
                     text = str(m.get("text", ""))
                     if sender >= 0 and text:
                         self._chat_bubbles[sender] = (text, now + 5.0)
                     if mid > max_id:
                         max_id = mid
                 self._last_chat_id_seen = max_id
             except Exception:
                 pass
        if self.game_manager.player is not None and self.online_manager is not None:
            player = self.game_manager.player
            self.online_manager.update(
                player.position.x,
                player.position.y,
                self.game_manager.current_map.path_name,
                player.direction.name.lower(),
                player.is_moving,
                player.animation.cur_row,
                player.animation.current_frame
            )
        
    @override
    def draw(self, screen: pg.Surface):        
        if self.game_manager.player:
            '''
            [TODO HACKATHON 3]
            Implement the camera algorithm logic here
            Right now it's hard coded, you need to follow the player's positions
            you may use the below example, but the function still incorrect, you may trace the entity.py
            
            camera = self.game_manager.player.camera
            '''
            camera = self.game_manager.player.camera
            self.game_manager.current_map.draw(screen, camera)
            self.game_manager.player.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)
        if hasattr(self.game_manager.current_map, "npcs"):
            for npc in self.game_manager.current_map.npcs:
                npc.draw(screen, self.game_manager.player.camera)

        #bag and pc
        self.game_manager.bag.draw(screen)
        self.game_manager.pc_box.draw(screen)

        #chat box
        if self.chat_overlay and self._chat_visible:
            self.chat_overlay.draw(screen)

        #online
        if self.online_manager and self.game_manager.player:
            if not hasattr(self, "remote_players"):
                self.remote_players = {}  # id → Animation

            list_online = self.online_manager.get_list_players()

            for p in list_online:
                if p["map"] != self.game_manager.current_map.path_name:
                    continue

                pid = p["id"]

                # create animation instance once
                if pid not in self.remote_players:
                    from src.sprites.animation import Animation
                    self.remote_players[pid] = Animation(
                        "character/ow1.png",    
                        ["down", "left", "right", "up"],
                        n_keyframes=4,
                        size=(GameSettings.TILE_SIZE, GameSettings.TILE_SIZE),
                        loop=1
                    )

                anim = self.remote_players[pid]

                # sync animation
                anim.set_state(p["anim"])
                anim.set_frame(p["frame"])

                # sync world → screen transform
                cam = self.game_manager.player.camera
                world_pos = Position(p["x"], p["y"])
                screen_pos = cam.transform_position_as_position(world_pos)

                anim.rect.x = screen_pos.x
                anim.rect.y = screen_pos.y

                anim.draw(screen)

            try:
                self._draw_chat_bubbles(screen, camera)
            except Exception as e:
                Logger.error(f"Bubble error: {e}")    

        #minimap
        self.minimap.draw(screen)
        
        #BAG OVERLAY
        self.bag_button.draw(screen)

        #setting
        self.settings_button.draw(screen)

        # NAV open button + text
        self.nav_open_button.draw(screen)
        nav_text = self.nav_small_font.render("NAV", True, (0, 0, 0))
        is_hover = (self.nav_open_button.img_button is self.nav_open_button.img_button_hover)
        if is_hover:
            screen.blit(
                nav_text,
                (
                    self.nav_open_button.hitbox.centerx - nav_text.get_width() // 2,
                    self.nav_open_button.hitbox.centery + 4 - nav_text.get_height() // 2
                )
            )
        else:
            screen.blit(
                nav_text,
                (
                    self.nav_open_button.hitbox.centerx - nav_text.get_width() // 2,
                    self.nav_open_button.hitbox.centery - nav_text.get_height() // 2
                )
            )

        #shop
        if self.game_manager.current_shop_overlay:
            self.game_manager.current_shop_overlay.draw(screen)
            if not self.game_manager.current_shop_overlay.is_open:
                self.game_manager.close_shop()
                
        
        

        #SETTING OVERLAY
        if self.show_settings:
            #Dim the background
            dim_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            dim_surface.fill((0, 0, 0, 160))
            screen.blit(dim_surface, (0, 0))

            # panel setup
            panel_width, panel_height = 550, 400  # wider panel
            panel_x = (GameSettings.SCREEN_WIDTH - panel_width) // 2
            panel_y = (GameSettings.SCREEN_HEIGHT - panel_height) // 2
            panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)

            # Shadow (simple bottom-right offset) 
            shadow_rect = panel_rect.move(6, 6)
            pg.draw.rect(screen, (50, 50, 50), shadow_rect, border_radius=20)

            # Main orange panel 
            pg.draw.rect(screen, (255, 165, 0), panel_rect, border_radius=20)

            # Border outline
            pg.draw.rect(screen, (0, 0, 0), panel_rect, 3, border_radius=20)

            #Title text
            font = pg.font.Font(None, 50)
            title = font.render("SETTINGS", True, (0, 0, 0))
            screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 30))
            # Volume Text
            small_font = pg.font.Font(None, 36)
            vol_text = small_font.render(f"Volume: {int(self.volume * 100)}%", True, (0, 0, 0))
            screen.blit(vol_text, (self.slider_rect.left, self.slider_rect.top - 30))

            # Slider
            pg.draw.rect(screen, (255, 255, 255), self.slider_rect, border_radius=5)
            pg.draw.rect(screen, (0, 0, 0), self.slider_rect, 1, border_radius=5)
            pg.draw.circle(screen, (0, 0, 0), self.slider_knob_rect.center, 12)
            pg.draw.circle(screen, (255, 255, 255), self.slider_knob_rect.center, 10)

            # Mute Text
            mute_text = small_font.render(f"Mute: {'On' if self.muted else 'Off'}", True, (0, 0, 0))
            screen.blit(mute_text, (self.toggle_rect.left, self.toggle_rect.top - 30))

            # Mute button
            bg_color = (0, 180, 0) if self.muted else (180, 0, 0)
            pg.draw.rect(screen, bg_color, self.toggle_rect, border_radius=10)
            pg.draw.rect(screen, (0, 0, 0), self.toggle_rect, 2, border_radius=10)
            knob_x = self.toggle_rect.right - 20 if self.muted else self.toggle_rect.left + 20 
            pg.draw.circle(screen, (255, 255, 255), (knob_x, self.toggle_rect.centery), 10)

            #save and load text
            
            save_text = small_font.render("SAVE", True, (0, 0, 0))
            load_text = small_font.render("LOAD", True, (0, 0, 0))

            screen.blit(save_text,
                        (
                            self.save_button.hitbox.left +3 ,
                            self.save_button.hitbox.top - save_text.get_height()
                        )
                    )

            screen.blit(load_text,
                        (
                            self.load_button.hitbox.left + 3,
                            self.load_button.hitbox.top - load_text.get_height()
                        )
                    )
            
            #save and load button
            self.save_button.draw(screen)
            self.load_button.draw(screen)


            # Back button
            self.back_button.draw(screen)
            self.x_button.draw(screen)

        #navigation
        if self.nav_overlay_open:
            dim = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            dim.fill((0, 0, 0, 180))
            screen.blit(dim, (0, 0))

            panel_w, panel_h = 420, 360
            panel_x = (GameSettings.SCREEN_WIDTH - panel_w) // 2
            panel_y = (GameSettings.SCREEN_HEIGHT - panel_h) // 2
            panel = pg.Rect(panel_x, panel_y, panel_w, panel_h)

            pg.draw.rect(screen, (255, 165, 0), panel, border_radius=16)
            pg.draw.rect(screen, (0, 0, 0), panel, 3, border_radius=16)

            title = self.nav_font.render("Select Destination", True, (0, 0, 0))
            screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 26))

            hint = self.nav_small_font.render("Click a map to auto-walk", True, (20, 20, 20))
            screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.top + 56))

            # draw map buttons + text labels
            for name, btn in self.nav_map_buttons:
                btn.draw(screen)
                label = self.nav_small_font.render(name, True, (0, 0, 0))
                is_hover = (btn.img_button is btn.img_button_hover)
                if is_hover:
                    screen.blit(
                        label,
                        (
                            btn.hitbox.centerx - label.get_width() // 2,
                            btn.hitbox.centery + 4 - label.get_height() // 2
                        )
                    )
                else:
                    screen.blit(
                        label,
                        (
                            btn.hitbox.centerx - label.get_width() // 2,
                            btn.hitbox.centery - label.get_height() // 2
                        )
                    )



    def _draw_chat_bubbles(self, screen: pg.Surface, camera: PositionCamera):
        if not self.online_manager:
            return

        now = time.monotonic()

        # Remove expired bubbles
        expired = [pid for pid, (_, ts) in self._chat_bubbles.items() if ts <= now]
        for pid in expired:
            del self._chat_bubbles[pid]

        if not self._chat_bubbles:
            return

        # draw local player first
        local_pid = self.online_manager.player_id
        font = pg.font.SysFont("Arial", 16)

        # Local player bubble
        if local_pid in self._chat_bubbles:
            text, _ = self._chat_bubbles[local_pid]
            self._draw_chat_bubble_for_pos(
                screen, camera, self.game_manager.player.position, text, font
            )

        # Other players
        for p in self.online_manager.get_list_players():
            pid = p["id"]
            if pid not in self._chat_bubbles:
                continue

            world_pos = Position(p["x"], p["y"])
            text, _ = self._chat_bubbles[pid]

            self._draw_chat_bubble_for_pos(
                screen, camera, world_pos, text, font
            )

    def _draw_chat_bubble_for_pos(self, screen, camera, world_pos, text, font):
        # Convert world → screen pos
        screen_pos = camera.transform_position_as_position(world_pos)
        sx = screen_pos.x + 32
        sy = screen_pos.y

        # Bubble appears slightly above head
        sy -= 20

        text_surf = font.render(text, True, (255,255,255))
        padding = 6
        w = text_surf.get_width() + padding * 2
        h = text_surf.get_height() + padding * 2

        # background
        bubble = pg.Surface((w, h), pg.SRCALPHA)
        bubble.fill((0,0,0,180))
        screen.blit(bubble, (sx - w//2, sy - h))

        # text
        screen.blit(text_surf, (sx - text_surf.get_width()//2, sy - h + padding))
            



