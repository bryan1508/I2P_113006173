import pygame as pg

from src.scenes.scene import Scene
from src.utils import Logger

class SceneManager:
    
    _scenes: dict[str, Scene]
    _current_scene: Scene | None = None
    _next_scene: str | None = None
    
    def __init__(self):
        Logger.info("Initializing SceneManager")
        self._scenes = {}
        self.transition_active = False
        self.transition_alpha = 0
        self.transition_speed = 400     # px per second (fade speed)
        self.transition_phase = "idle"  # 'fade_out', 'fade_in', or 'idle'

        self.fade_surface = pg.Surface((1280, 720)) 
        self.fade_surface.fill((0, 0, 0))
        
    def register_scene(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene
        
    def get_scene(self, name: str) -> Scene:
        return self._scenes[name]
        
    def change_scene(self, scene_name: str) -> None:
        if scene_name in self._scenes:
            Logger.info(f"Changing scene to '{scene_name}'")
            self._next_scene = scene_name
            self.transition_active = True
            self.transition_phase = "fade_out"
            self.transition_alpha = 0
        else:
            raise ValueError(f"Scene '{scene_name}' not found")
            
    def update(self, dt: float) -> None:
        # Handle scene transition
        if self.transition_active:
            self._update_transition(dt)
            return
    
        
        # Update current scene
        if self._current_scene:
            self._current_scene.update(dt)
            
    def draw(self, screen: pg.Surface) -> None:
        
        if self._current_scene:
            self._current_scene.draw(screen)
        if self.transition_active:
            self.fade_surface.set_alpha(int(self.transition_alpha))
            screen.blit(self.fade_surface, (0, 0))
            
    def _perform_scene_switch(self) -> None:
        if self._next_scene is None:
            return
            
        # Exit current scene
        if self._current_scene:
            self._current_scene.exit()
        
        self._current_scene = self._scenes[self._next_scene]
        
        # Enter new scene
        if self._current_scene:
            Logger.info(f"Entering {self._next_scene} scene")
            self._current_scene.enter()
            
        # Clear the transition request
        self._next_scene = None
    def _update_transition(self, dt):
        if self.transition_phase == "fade_out":
            self.transition_alpha += self.transition_speed * dt

            if self.transition_alpha >= 255:
                self.transition_alpha = 255
                
                # Perform the scene switch
                self._perform_scene_switch()

                # Start fade-in
                self.transition_phase = "fade_in"

        elif self.transition_phase == "fade_in":
            self.transition_alpha -= self.transition_speed * dt

            if self.transition_alpha <= 0:
                self.transition_alpha = 0
                self.transition_active = False
                self.transition_phase = "idle"
        