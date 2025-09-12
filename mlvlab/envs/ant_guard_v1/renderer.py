import arcade
import numpy as np
import math
import random
import time
from typing import Dict, Any

try:
    from .constants import C
except ImportError:
    # Fallback para ejecución directa
    from constants import C


class Particle(arcade.SpriteCircle):
    """Partícula de ácido simple usando Sprites de Arcade (Requisito 6.2)."""

    def __init__(self, position, velocity, lifespan):
        super().__init__(radius=4, color=C.COLOR_ACID)
        self.center_x, self.center_y = position
        self.change_x, self.change_y = velocity
        self.lifespan = lifespan
        self.max_lifespan = lifespan

    def update(self):
        super().update()
        self.lifespan -= 1
        self.alpha = int(255 * (self.lifespan / self.max_lifespan))
        if self.lifespan < 20:
            self.scale *= 0.95

        if self.lifespan <= 0:
            self.remove_from_sprite_lists()


class AntGuardRenderer:
    """
    Renderiza el entorno AntGuard-v1 usando Arcade.
    """

    def __init__(self, render_mode: str):
        self.mode = render_mode
        self.window: arcade.Window | None = None
        self.initialized = False
        self.particle_list = None
        self.game_over_sprite = None

        self.game_state: Dict[str, Any] | None = None

        self.ant_display_pos = [0.0, 0.0]
        self.randomized_ant_color = (0, 0, 0)
        self.ant_size_multipliers = {
            'head': 1.0, 'thorax': 1.0, 'abdomen': 1.0}
        self.rng_visual = np.random.default_rng()
        self.last_time = 0

    def _initialize(self):
        if self.initialized:
            return

        self.width = C.SCREEN_WIDTH
        self.height = C.WINDOW_HEIGHT

        self.window = arcade.Window(
            self.width, self.height, "AntGuard-v1: Tactical Defender", visible=(self.mode == "human")
        )
        arcade.set_background_color(C.COLOR_BG_OUTSIDE)

        self.particle_list = arcade.SpriteList()
        self.initialized = True
        self.last_time = time.time()

    def reset(self):
        if self.particle_list:
            self.particle_list.clear()
        self.game_over_sprite = None

        r_var, g_var, b_var = self.rng_visual.integers(-20, 21, size=3)
        base_color = (192, 57, 43)
        r = max(0, min(255, base_color[0] + r_var))
        g = max(0, min(255, base_color[1] + g_var))
        b = max(0, min(255, base_color[2] + b_var))
        self.randomized_ant_color = (r, g, b)

        self.ant_size_multipliers = {
            'head': self.rng_visual.uniform(0.8, 1.2),
            'thorax': self.rng_visual.uniform(0.8, 1.2),
            'abdomen': self.rng_visual.uniform(0.8, 1.2)
        }

    def _world_to_screen(self, x, y):
        tunnel_height_ratio = 0.9
        game_height_px = C.GAME_HEIGHT * tunnel_height_ratio

        sy = (y / C.WORLD_HEIGHT) * game_height_px + \
            (C.GAME_HEIGHT * (1 - tunnel_height_ratio))

        width_at_y = C.WORLD_WIDTH_BOTTOM + \
            (C.WORLD_WIDTH_TOP - C.WORLD_WIDTH_BOTTOM) * (y / C.WORLD_HEIGHT)
        sx = (x / (width_at_y / 2)) * (self.width / 2) + (self.width / 2)

        return sx, sy

    def _draw_background(self):
        arcade.draw_lrbt_rectangle_filled(
            0, self.width, 0, C.GAME_HEIGHT, C.COLOR_BG_TUNNEL)

        points = [
            self._world_to_screen(-C.WORLD_WIDTH_BOTTOM / 2, 0),
            self._world_to_screen(C.WORLD_WIDTH_BOTTOM / 2, 0),
            self._world_to_screen(C.WORLD_WIDTH_TOP / 2, C.WORLD_HEIGHT),
            self._world_to_screen(-C.WORLD_WIDTH_TOP / 2, C.WORLD_HEIGHT)
        ]
        arcade.draw_polygon_outline(points, C.COLOR_WALL, 5)

    def _draw_ant(self):
        if not self.game_state:
            return

        base_sx, base_sy = self._world_to_screen(0, 0)
        angle_deg = math.degrees(self.game_state.get('ant_angle', 0)) + 90

        self.ant_display_pos[0] = base_sx
        self.ant_display_pos[1] = base_sy

        ax, ay = self.ant_display_pos
        t = time.time()

        base_color = self.randomized_ant_color
        body_c = base_color
        leg_c = tuple(max(0, c - 50) for c in base_color)
        shadow_c = tuple(int(c * 0.3) for c in base_color) + (180,)
        eye_c = (30, 30, 30)

        m_head = self.ant_size_multipliers['head']
        m_thorax = self.ant_size_multipliers['thorax']
        m_abdomen = self.ant_size_multipliers['abdomen']

        ant_base_size = C.SPIDER_RADIUS * 4
        hr = ant_base_size * 0.4 * m_head
        trx = ant_base_size * 0.5 * m_thorax
        trya = ant_base_size * 0.45 * m_thorax
        arx = ant_base_size * 0.7 * m_abdomen
        ary = ant_base_size * 0.55 * m_abdomen

        rad = math.radians(angle_deg)
        def rotate(x, y): return x * math.cos(rad) - y * \
            math.sin(rad), x * math.sin(rad) + y * math.cos(rad)

        speed, leg_o, ant_o = 3.0, 3, 5
        bounce = abs(math.sin(t * 3.0)) * 2
        osc = math.sin(t * speed)

        draw_cx, draw_cy = ax, ay + bounce

        ll, lt = ant_base_size * 0.7, 3
        for side in [-1, 1]:
            for i, off_a in enumerate([-40, 0, 40]):
                co = osc if (side == 1 and i != 1) or (
                    side == -1 and i == 1) else -osc
                end_a = angle_deg + (90 + off_a + co * leg_o) * side
                ex, ey = math.cos(math.radians(end_a)) * \
                    ll, math.sin(math.radians(end_a)) * ll
                arcade.draw_line(draw_cx, draw_cy, draw_cx +
                                 ex, draw_cy + ey, leg_c, lt)

        sx, sy = 3, -3
        ax_r, ay_r = rotate(-(trx + arx * 0.5), 0)
        arcade.draw_ellipse_filled(
            draw_cx + ax_r + sx, draw_cy + ay_r + sy, arx, ary, shadow_c, angle_deg)
        arcade.draw_ellipse_filled(
            draw_cx + ax_r, draw_cy + ay_r, arx, ary, body_c, angle_deg)
        arcade.draw_ellipse_filled(
            draw_cx + sx, draw_cy + sy, trx, trya, shadow_c, angle_deg)
        arcade.draw_ellipse_filled(
            draw_cx, draw_cy, trx, trya, body_c, angle_deg)

        hx_r, hy_r = rotate(hr * 0.85 + trx, 0)
        arcade.draw_circle_filled(
            draw_cx + hx_r + sx, draw_cy + hy_r + sy, hr, shadow_c)
        arcade.draw_circle_filled(draw_cx + hx_r, draw_cy + hy_r, hr, body_c)

        er, eox, eoy = hr * 0.3, hr * 0.4, hr * 0.65
        for side in [-1, 1]:
            ex_r, ey_r = rotate(eox, eoy * side)
            arcade.draw_circle_filled(
                draw_cx + hx_r + ex_r, draw_cy + hy_r + ey_r, er, eye_c)

        al, at = hr * 1.8, 2
        ant_o_val = osc * ant_o
        for side in [-1, 1]:
            end_a = angle_deg + (45 * side) + ant_o_val
            asx_r, asy_r = rotate(hr * 0.9, hr * 0.4 * side)
            asx, asy = draw_cx + hx_r + asx_r, draw_cy + hy_r + asy_r
            aex, aey = math.cos(math.radians(end_a)) * \
                al, math.sin(math.radians(end_a)) * al
            arcade.draw_line(asx, asy, asx + aex, asy + aey, leg_c, at)

        # --- ELIMINADO: Indicador de disparo (cañón) que causaba confusión ---
        # Ya no se dibuja la línea blanca estática.

        # Animación de disparo (fogonazo)
        if self.game_state.get('info', {}).get('event') == 'spit':
            arcade.draw_circle_outline(
                ax, ay, ant_base_size * 1.2, arcade.color.WHITE, 3, num_segments=50)

    def _draw_spider(self):
        if not self.game_state or self.game_state.get('spider_health', 0) <= 0:
            return

        spider_x, spider_y = self.game_state.get('spider_pos', (0, 0))
        sx, sy = self._world_to_screen(spider_x, spider_y)

        if self.game_state.get('info', {}).get('event') == 'hit':
            sx += random.uniform(-5, 5)
            sy += random.uniform(-5, 5)

        t = time.time()
        base_size = C.SPIDER_RADIUS * 5
        body_color = (40, 10, 50)
        leg_color = (20, 5, 25)
        eye_color = (255, 0, 50)

        abdomen_w, abdomen_h = base_size * 1.2, base_size * 1.5
        head_w, head_h = base_size, base_size

        arcade.draw_ellipse_filled(
            sx, sy - base_size * 0.4, abdomen_w, abdomen_h, body_color)
        arcade.draw_ellipse_filled(
            sx, sy + base_size * 0.5, head_w, head_h, body_color)

        leg_length = base_size * 2.5
        leg_thickness = 4
        leg_oscillation = math.sin(t * 15) * 10

        for i in range(4):
            angle_offset = 25 + i * 25
            arcade.draw_line(
                sx, sy,
                sx + math.cos(math.radians(angle_offset +
                              leg_oscillation)) * leg_length,
                sy + math.sin(math.radians(angle_offset +
                              leg_oscillation)) * leg_length,
                leg_color, leg_thickness
            )
            arcade.draw_line(
                sx, sy,
                sx + math.cos(math.radians(180 - angle_offset -
                              leg_oscillation)) * leg_length,
                sy + math.sin(math.radians(180 - angle_offset -
                              leg_oscillation)) * leg_length,
                leg_color, leg_thickness
            )

        for i in range(4):
            offset_x = (i - 1.5) * 5
            arcade.draw_circle_filled(
                sx + offset_x, sy + base_size * 0.7, 2, eye_color)

    def _draw_ui(self):
        if not self.game_state:
            return

        health_ratio = self.game_state.get(
            'spider_health', 0) / C.SPIDER_HEALTH_MAX
        arcade.draw_lrbt_rectangle_filled(
            0, self.width * health_ratio, C.WINDOW_HEIGHT - 10, C.WINDOW_HEIGHT, arcade.color.RED)

        y_start = C.GAME_HEIGHT + C.UI_HEIGHT / 2
        for i in range(C.ANT_ACID_TANK_MAX):
            color = C.COLOR_ACID if i < self.game_state.get(
                'ant_acid_tank', 0) else arcade.color.GRAY
            arcade.draw_circle_filled(30 + i * 25, y_start, 10, color)

        if self.game_state.get('cooldown_timer', 0) > 0:
            cooldown_ratio = self.game_state.get(
                'cooldown_timer', 0) / C.SPIT_COOLDOWN_FRAMES_MAX
            arcade.draw_lrbt_rectangle_filled(
                0, self.width, C.GAME_HEIGHT - 5, C.GAME_HEIGHT,
                (255, 255, 255, 100)
            )
            arcade.draw_lrbt_rectangle_filled(
                0, self.width * cooldown_ratio, C.GAME_HEIGHT - 5, C.GAME_HEIGHT,
                arcade.color.LIGHT_BLUE
            )

    def _update_particles(self):
        if not self.game_state or not self.particle_list:
            return

        event = self.game_state.get('info', {}).get('event')
        if event == 'spit':
            ant_sx, ant_sy = self._world_to_screen(0, 0)
            angle_rad = self.game_state.get('ant_angle', 0)
            for _ in range(10):
                speed = random.uniform(8, 14)
                vel = (-speed * math.sin(angle_rad),
                       speed * math.cos(angle_rad))
                p = Particle((ant_sx, ant_sy), vel, lifespan=40)
                self.particle_list.append(p)

        elif event == 'hit':
            spider_x, spider_y = self.game_state.get('spider_pos', (0, 0))
            spider_sx, spider_sy = self._world_to_screen(spider_x, spider_y)
            for _ in range(20):
                vel = (random.uniform(-3, 3), random.uniform(-3, 3))
                p = Particle((spider_sx, spider_sy), vel, lifespan=20)
                self.particle_list.append(p)

        self.particle_list.update()

    def update(self, state: Dict[str, Any]):
        if not self.initialized:
            self._initialize()

        if not self.window:
            return None

        self.game_state = state

        try:
            self.window.switch_to()
            self.window.clear()
        except Exception:
            return None

        self._draw_background()
        self._draw_ant()
        self._draw_spider()
        self._update_particles()
        self.particle_list.draw()
        self._draw_ui()

        if self.game_state and self.game_state.get('game_over', False):
            msg = "VICTORIA" if self.game_state.get(
                'spider_health', 0) <= 0 else "DERROTA"
            arcade.draw_text(msg, self.width/2, self.height/2,
                             arcade.color.WHITE, 40, anchor_x="center")

        if self.mode == "rgb_array":
            try:
                image_rgba = arcade.get_image()
                image_rgb = image_rgba.convert("RGB")
                return np.array(image_rgb)
            except Exception:
                return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        return None
