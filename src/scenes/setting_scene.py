import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

class SettingScene(Scene):
    def __init__(self):
        super().__init__()
        self.panel_width = 550
        self.panel_height = 400
        self.panel_color = (255, 165, 0)  
        self.shadow_color = (50, 50, 50) 

        self.panel_rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - self.panel_width) // 2,
            (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2,
            self.panel_width,
            self.panel_height,
        )

        self.back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            GameSettings.SCREEN_WIDTH // 2 + 170,
            GameSettings.SCREEN_HEIGHT // 2 + 130,
            80,
            50,
            lambda: scene_manager.change_scene("menu")
        )

        
        self.background = BackgroundSprite("backgrounds/background1.png")

        self.volume = GameSettings.AUDIO_VOLUME
        self.muted = GameSettings.AUDIO_MUTED

        self.slider_rect = pg.Rect(self.panel_rect.left + 100, self.panel_rect.top + 170, 350, 10)
        self.slider_knob_rect = pg.Rect(0, 0, 20, 20)
        self._update_knob_pos()

        self.toggle_rect = pg.Rect(self.panel_rect.left + 100, self.panel_rect.top + 225, 80, 30)

        self.dragging = False

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

    @override
    def enter(self) -> None:
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
        self.volume = GameSettings.AUDIO_VOLUME
        self.muted = GameSettings.AUDIO_MUTED
        self._update_knob_pos()
        if(GameSettings.AUDIO_MUTED):
            sound_manager.pause_all()
        pass
    @override
    def update(self, dt: float) -> None:
        if input_manager.key_pressed(pg.K_ESCAPE):
            scene_manager.change_scene("menu")
            return
        self.back_button.update(dt)

        #Volume slider drag
        mouse_pressed = pg.mouse.get_pressed()[0]
        mouse_x, mouse_y = pg.mouse.get_pos()

        if mouse_pressed and self.slider_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
        if not mouse_pressed:
            self.dragging = False

        if self.dragging:
            rel_x = mouse_x - self.slider_rect.left
            rel_x = max(0, min(self.slider_rect.width, rel_x))
            self.volume = rel_x / self.slider_rect.width
            GameSettings.AUDIO_VOLUME = self.volume

            # Update currently playing music
            if sound_manager.current_bgm :
                sound_manager.current_bgm.set_volume(self.volume)
            self._update_knob_pos()
        if input_manager.mouse_pressed(pg.BUTTON_LEFT):  
            mouse_x, mouse_y = pg.mouse.get_pos()
            if self.toggle_rect.collidepoint(mouse_x, mouse_y):
                self.toggle_mute()
    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        #Dim background
        dim_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
        dim_surface.fill((0, 0, 0, 160))  
        screen.blit(dim_surface, (0, 0))

        #Draw shadow 
        shadow_rect = self.panel_rect.move(6, 6)
        pg.draw.rect(screen, self.shadow_color, shadow_rect, border_radius=20)

        #Draw main orange panel
        pg.draw.rect(screen, self.panel_color, self.panel_rect, border_radius=20)
        pg.draw.rect(screen, (0, 0, 0), self.panel_rect, 3, border_radius=20)

        #Title
        font = pg.font.Font(None, 50)
        title = font.render("SETTINGS", True, (0, 0, 0))
        screen.blit(title, (self.panel_rect.centerx - title.get_width() // 2, self.panel_rect.top + 45))

        #Back button 
        self.back_button.draw(screen)


        #volume text
        small_font = pg.font.Font(None, 36)
        vol_text = small_font.render(f"Volume: {int(self.volume * 100)}%", True, (0, 0, 0))
        screen.blit(vol_text, (self.slider_rect.left, self.slider_rect.top - 30))
        #volume slider
        pg.draw.rect(screen, (255, 255, 255), self.slider_rect, border_radius=5)
        pg.draw.rect(screen, (0, 0, 0), self.slider_rect,1,border_radius=5)
        pg.draw.circle(screen, (0, 0, 0), self.slider_knob_rect.center, 12)
        pg.draw.circle(screen, (255, 255, 255), self.slider_knob_rect.center, 10)

        #Mute Label
        mute_text = small_font.render(f"Mute: {'On' if self.muted else 'Off'}", True, (0, 0, 0))
        screen.blit(mute_text, (self.slider_rect.left, self.slider_rect.top + 27))

        #mute button
        bg_color = (0, 180, 0) if self.muted else (180, 0, 0)
        pg.draw.rect(screen, bg_color, self.toggle_rect, border_radius=10)
        pg.draw.rect(screen, (0, 0, 0), self.toggle_rect, 2, border_radius=10)
        # knob inside toggle
        knob_x = self.toggle_rect.right - 20 if self.muted else self.toggle_rect.left + 20
        pg.draw.circle(screen, (255, 255, 255), (knob_x, self.toggle_rect.centery), 10)
'''
[TODO HACKATHON 5]
Try to mimic the menu_scene.py or game_scene.py to create this new scene
'''