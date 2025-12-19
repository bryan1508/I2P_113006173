import pygame as pg
from typing import TYPE_CHECKING

# Assuming these imports are correct based on your file structure
from src.utils import GameSettings, Position
from src.interface.components import Button
from src.core.services import input_manager
from src.sprites import Sprite

# Type checking imports help with avoiding circular dependencies
if TYPE_CHECKING:
    from src.data.bag import Bag
    from src.data.shop import Shop


class ShopOverlay:
    def __init__(self, shop: "Shop", bag: "Bag") -> None:
        self.shop = shop
        self.bag = bag

        # Panel size
        self.panel_w = 550
        self.panel_h = 500
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_w) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_h) // 2
        self.panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_w, self.panel_h)

        # UI fonts
        self.font_title = pg.font.Font(None, 50)
        self.font = pg.font.Font(None, 26)
        self.font_price = pg.font.Font(None, 30) 

        # State - START IN NONE MODE
        self.is_open = True
        self.mode = None  # None means showing Buy/Sell buttons
        self.hover_index = -1
        
        # --- SCROLL VARIABLES (RE-ADDED) ---
        self.scroll = 0
        self.scroll_speed = 40 
        self.max_scroll = 0
        
        # Item list parameters
        self.item_list_start_y = self.panel_y + 100
        self.item_spacing = 65 
        self.item_row_w = 470
        self.item_row_h = 60
        self.item_row_x_start = self.panel_x + (self.panel_w - self.item_row_w) // 2
        
        # Calculate the visible list height (Area where we draw the scrollable content)
        list_visible_h = self.panel_y + self.panel_h - 100 - self.item_list_start_y
        
        # The scrollable area rect (for mouse wheel detection and final blit clipping)
        self.scroll_area = pg.Rect(
            self.item_row_x_start, 
            self.item_list_start_y, 
            self.item_row_w, 
            list_visible_h 
        )
        # ------------------------------------

        # Close button
        self.close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            self.panel_x + self.panel_w - 60,
            self.panel_y + 15,
            40, 40,
            self.close
        )
        # Back button
        self.back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            self.panel_x + 15,
            self.panel_y + 15,
            40, 40,
            self.switch_to_none
        )
        # For click cooldown
        self.last_click = 0

        # Button dimensions for buy and sell (in None mode)
        self.button_w = 470
        self.button_h = 120
        self.button_margin = 20

        # Rectangles for the buy and sell buttons (in None mode)
        self.buy_button_rect = pg.Rect(self.panel_x + self.button_margin + 20, self.panel_y + 120, self.button_w, self.button_h)
        self.sell_button_rect = pg.Rect(self.panel_x + self.button_margin + 20, self.panel_y + 120 + 160, self.button_w, self.button_h)
        
        # Item buttons list
        self.item_buttons = []

    # shop button
    def _create_item_buttons(self):
        self.item_buttons = []
        
        entries = []
        if self.mode == "buy":
            entries = self.shop.items_for_sale
        elif self.mode == "sell":
            entries = [item for item in self.bag._items_data if item["name"].lower() != "coins"]

        for idx, item in enumerate(entries):
            # Calculate absolute screen position for the button (used for initial hitbox)
            button_x = self.item_row_x_start + self.item_row_w - 70 
            button_y = self.item_list_start_y + idx * self.item_spacing + 10
            
            button = Button(
                "UI/button_shop.png",
                "UI/button_shop_hover.png",
                button_x, 
                button_y,
                40, 40,
                lambda original_idx=idx: self._mouse_confirm(original_idx)
            )
            self.item_buttons.append(button)

    # ----------------------------------------------------
    # CLOSE OVERLAY / MODE SWITCHING
    # ----------------------------------------------------
    def close(self):
        self.is_open = False

    def switch_to_buy(self):
        self.mode = "buy"
        self.scroll = 0 # Reset scroll
        self._create_item_buttons() 

    def switch_to_sell(self):
        self.mode = "sell"
        self.scroll = 0 # Reset scroll
        self._create_item_buttons() 

    def switch_to_none(self):
        self.mode = None
        self.item_buttons = [] 

    # ----------------------------------------------------
    # UPDATE (handles mouse and scrolling)
    # ----------------------------------------------------
    def update(self, dt):
        mx, my = pg.mouse.get_pos()
        m_pressed = input_manager.mouse_pressed(pg.BUTTON_LEFT)

        self.close_button.update(dt)

        if self.mode is None:
            if m_pressed and (pg.time.get_ticks() - self.last_click > 200):
                self.last_click = pg.time.get_ticks()
                if self.buy_button_rect.collidepoint(mx, my):
                    self.switch_to_buy()
                elif self.sell_button_rect.collidepoint(mx, my):
                    self.switch_to_sell()

        elif self.mode in ["buy", "sell"]:
            self.back_button.update(dt)

            # --- SCROLL LOGIC ---
            mouse_wheel = input_manager.mouse_wheel
            if self.scroll_area.collidepoint(mx, my):
                if mouse_wheel != 0 :
                    self.scroll += mouse_wheel * self.scroll_speed
                    # Quick clamp using max_scroll. Final clamping happens in draw()
                    self.scroll = min(0, max(self.scroll, self.max_scroll))
            # --------------------
            
            self.hover_index = -1
            
            entries = self.shop.items_for_sale if self.mode == "buy" else [
                item for item in self.bag._items_data if item["name"].lower() != "coins"
            ]
            
            for idx, item in enumerate(entries):
                # Update the button's absolute screen position (hitbox) for click detection
                if idx < len(self.item_buttons):
                    # Calculate the button's Y position INCLUDING scroll offset
                    button_y_with_scroll = self.item_list_start_y + idx * self.item_spacing + 10 + self.scroll
                    
                    # Update the button's hitbox for correct collision
                    self.item_buttons[idx].hitbox.y = button_y_with_scroll
                    self.item_buttons[idx].update(dt)
                    
                # Define the clickable area for the entire item row, applying the scroll offset
                row_rect = pg.Rect(
                    self.item_row_x_start, 
                    self.item_list_start_y + idx * self.item_spacing + self.scroll, # ADD SCROLL
                    self.item_row_w, 
                    self.item_row_h
                )
                
                # Check for hover only if the item row is currently visible
                if self.scroll_area.colliderect(row_rect) and row_rect.collidepoint(mx, my):
                    self.hover_index = idx
                    break 

        # Check for ESC (should still close)
        if input_manager.key_pressed(pg.K_ESCAPE):
            if self.mode is None:
                self.is_open = False
            else:
                self.switch_to_none()


    # ----------------------------------------------------
    # Mouse triggered buy/sell (from cart button click)
    # ----------------------------------------------------
    def _mouse_confirm(self, original_idx):
        if pg.time.get_ticks() - self.last_click < 200:
             return
        self.last_click = pg.time.get_ticks()
        
        if self.mode == "buy":
            if original_idx < len(self.shop.items_for_sale):
                self.shop.buy(self.bag, original_idx)
        elif self.mode == "sell":
            sellable_items = [item for item in self.bag._items_data if item["name"].lower() != "coins"]
            if original_idx < len(sellable_items):
                item = sellable_items[original_idx]
                sell_price = item.get("sell_price", 1) 
                self.shop.sell(self.bag, item["name"], price=sell_price) 

    # ----------------------------------------------------
    # DRAW UI
    # ----------------------------------------------------
    def draw(self, screen: pg.Surface):
        # Dim background
        dim = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        screen.blit(dim, (0, 0))

        # Panel shadow and background
        pg.draw.rect(screen, (50, 50, 50), self.panel_rect.move(6, 6), border_radius=20)
        pg.draw.rect(screen, (240, 150, 50), self.panel_rect, border_radius=20)
        pg.draw.rect(screen, (0, 0, 0), self.panel_rect, 3, border_radius=20)

        # Title
        title = "Shop"
        if self.mode == "buy":
            title += " — Buy Items"
        elif self.mode == "sell":
            title += " — Sell Items"
        txt = self.font_title.render(title, True, (0, 0, 0))
        screen.blit(txt, (self.panel_rect.centerx - txt.get_width() // 2, self.panel_y + 30))
        
        # --- MODE: NONE (Buy/Sell Menu) ---
        if self.mode is None:
            self._draw_button(screen, self.buy_button_rect, "Buy Items", (255, 255, 255))
            self._draw_button(screen, self.sell_button_rect, "Sell Items", (255, 255, 255))

        # --- MODE: BUY or SELL (Item List) ---
        elif self.mode in ["buy", "sell"]:
            
            # 1. Structure the data
            entries = []
            if self.mode == "buy":
                entries = [(item, item.sprite_path, item.name, item.price, 1) for item in self.shop.items_for_sale]
            elif self.mode == "sell":
                sellable_items = [item for item in self.bag._items_data if item["name"].lower() != "coins"]
                entries = [(item, item["sprite_path"], item["name"], item.get("sell_price", 1), item["count"]) for item in sellable_items]

            # 2. Setup Scrollable Surface
            list_visible_h = self.scroll_area.height
            total_content_h = len(entries) * self.item_spacing
            
            # Recalculate max_scroll and clamp current scroll
            # Add a small buffer (e.g., 5 pixels) to max_scroll for safety margin if needed
            self.max_scroll = min(0, list_visible_h - total_content_h)
            self.scroll = min(0, max(self.scroll, self.max_scroll))
            
            # The surface must be large enough to hold all items
            item_list_surface = pg.Surface((self.scroll_area.width, max(list_visible_h, total_content_h)), pg.SRCALPHA)
            
            # 3. Draw Item Rows onto the temporary surface
            for idx, (item_data, sprite_path, item_name, item_price, item_count) in enumerate(entries):
                
                # Y position relative to the top of item_list_surface (unscrolled)
                y_on_surface = idx * self.item_spacing 
                
                # Rectangle definition relative to item_list_surface
                row_rect_on_surface = pg.Rect(5, y_on_surface + 5, self.item_row_w - 10, self.item_row_h - 10)
                
                # Row Background (Drawn directly on the temporary surface)
                row_bg_rect = row_rect_on_surface.inflate(-5, -5)
                pg.draw.rect(item_list_surface, (255, 240, 200), row_bg_rect, border_radius=6)
                pg.draw.rect(item_list_surface, (0, 0, 0), row_bg_rect, 2, border_radius=6) 

                # Highlight on hover
                if idx == self.hover_index:
                    pg.draw.rect(item_list_surface, (255, 255, 255), row_rect_on_surface.inflate(10, 10), 2, border_radius=6)

                # --- Item Visuals ---
                new_sprite_size = 30
                name_block_start_x = row_rect_on_surface.x + new_sprite_size + 20 
                text_center_y = row_rect_on_surface.centery
                
                # 3. Draw item sprite
                item_sprite = Sprite(sprite_path, (new_sprite_size, new_sprite_size)) 
                item_sprite.update_pos(Position(row_rect_on_surface.x + 15, text_center_y - new_sprite_size // 2))
                item_sprite.draw(item_list_surface) 

                # 4 & 5. Draw name and quantity (Directly onto the temporary surface)
                name_txt = self.font.render(item_name, True, (0, 0, 0)) 
                count_txt = self.font.render(f"x{item_count}", True, (0, 0, 0))
                
                name_y = text_center_y - name_txt.get_height() // 2
                
                # Calculate required positions for drawing on item_list_surface
                name_x = name_block_start_x 
                count_x = name_x + name_txt.get_width() + 10 
                
                item_list_surface.blit(name_txt, (name_x, name_y))
                item_list_surface.blit(count_txt, (count_x, name_y))
                
                # 6. Draw Price
                price_text = f"${item_price}" 
                price_txt = self.font_price.render(price_text, True, (255, 0, 0))
                price_y = text_center_y - price_txt.get_height() // 2
                price_x = row_rect_on_surface.x + row_rect_on_surface.width - price_txt.get_width() - 80
                item_list_surface.blit(price_txt, (price_x, price_y))

                # 7. Draw the Cart Button
                if idx < len(self.item_buttons):
                    # Button X position relative to item_list_surface (470-70 = 400)
                    button_x_on_surface = self.item_row_w - 70 
                    button_y_on_surface = y_on_surface + 10 
                    
                    # Store original absolute position before drawing manipulation
                    original_x = self.item_buttons[idx].hitbox.x
                    original_y = self.item_buttons[idx].hitbox.y
                    
                    # Set position relative to the temporary surface (0,0) for drawing
                    self.item_buttons[idx].hitbox.x = button_x_on_surface
                    self.item_buttons[idx].hitbox.y = button_y_on_surface 
                    
                    self.item_buttons[idx].draw(item_list_surface)
                    
                    # RESTORE original absolute position for next update cycle
                    self.item_buttons[idx].hitbox.x = original_x
                    self.item_buttons[idx].hitbox.y = original_y
            
            # 4. Blit the scrolled portion of the surface onto the screen
            # This is where the magic happens: only a scrolled section is visible
            screen.blit(
                item_list_surface, 
                self.scroll_area.topleft, 
                (0, -self.scroll, self.scroll_area.width, self.scroll_area.height)
            )

        # --- Coins Display ---
        coins = 0
        coin_pos = Position(self.panel_x + 40, self.panel_y + self.panel_h - 60)
        
        coin_data = next((item for item in self.bag._items_data if item["name"].lower() == "coins"), None)
        
        if coin_data:
            coins = coin_data["count"]
            coin_sprite = Sprite(coin_data["sprite_path"], (20, 20))
            coin_sprite.update_pos(coin_pos)
            
            coin_txt = self.font.render(f"Coins: {coins}", True, (0, 0, 0))
            coin_sprite.draw(screen)
            screen.blit(coin_txt, (coin_pos.x + 25, coin_pos.y + 2))

        # Draw persistent buttons LAST to ensure they are on top of the list
        if self.mode in ["buy", "sell"]:
            self.back_button.draw(screen) 
            
        self.close_button.draw(screen)

    # ----------------------------------------------------
    # Draw a Button (manual button without image)
    # ----------------------------------------------------
    def _draw_button(self, screen: pg.Surface, rect: pg.Rect, text: str, color: tuple):
        pg.draw.rect(screen, color, rect, border_radius=10)
        
        mx, my = pg.mouse.get_pos()
        if rect.collidepoint(mx, my):
            pg.draw.rect(screen, (0, 0, 0), rect, 4, border_radius=10)
        else:
            pg.draw.rect(screen, (0, 0, 0), rect, 2, border_radius=10) 

        button_text = self.font_title.render(text, True, (0, 0, 0))
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)