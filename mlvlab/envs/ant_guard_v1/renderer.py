# renderer.py
import numpy as np
import math
import random
import time
from typing import Dict, Any, Tuple, Optional

try:
    # Importamos ARCADE_AVAILABLE para manejar la compatibilidad
    from .constants import C, ARCADE_AVAILABLE
    if ARCADE_AVAILABLE:
        import arcade
except ImportError:
    # Fallback para ejecución directa
    from constants import C
    try:
        import arcade
        ARCADE_AVAILABLE = True
    except ImportError:
        ARCADE_AVAILABLE = False

# Si Arcade no está disponible, definimos clases dummy.
if ARCADE_AVAILABLE:
    class Particle(arcade.SpriteCircle):
        """Partícula mejorada. Usa unidades de tiempo real (segundos)."""

        def __init__(self, radius: float, color: Tuple, position: Tuple, velocity: Tuple, lifespan: float):
            # velocity es Pixels/Second, lifespan es Seconds.
            super().__init__(radius=int(radius), color=color)
            self.center_x, self.center_y = position
            self.velocity_x, self.velocity_y = velocity
            self.lifespan = lifespan
            self.max_lifespan = lifespan

        # Usamos on_update para movimiento basado en tiempo real (estándar de Arcade)
        def on_update(self, delta_time: float = 1/60):
            # Actualizar posición basada en velocidad y delta_time
            self.center_x += self.velocity_x * delta_time
            self.center_y += self.velocity_y * delta_time

            self.lifespan -= delta_time

            if self.lifespan <= 0:
                self.remove_from_sprite_lists()
                return

            # Efecto de desvanecimiento (Fade out)
            progress = max(0.0, self.lifespan / self.max_lifespan)
            self.alpha = int(255 * progress**0.5)

            # Efecto de encogimiento (Shrink) independiente del frame-rate
            if progress < 0.5:
                # Tasa de decaimiento por segundo (Decae al 10% de su tamaño en 1 segundo).
                decay_rate_per_sec = 0.1
                # Usamos decaimiento exponencial: scale *= factor^dt
                self.scale *= pow(decay_rate_per_sec, delta_time)

    # --- NUEVA CLASE DE PROYECTIL VISUAL (VERSIÓN ROBUSTA) ---
    class VisualSpit(arcade.SpriteCircle):
        """
        Un proyectil visual completamente desacoplado de la lógica del juego.
        Se mueve de un punto A a un punto B a velocidad constante y tiene
        una vida útil mínima para garantizar que sea visible.
        """

        def __init__(self, start_pos_world: np.ndarray, target_pos_world: np.ndarray, renderer: 'AntGuardRenderer'):
            super().__init__(radius=8, color=C.COLOR_ACID)  # Más grande para visibilidad
            self.renderer = renderer
            self.world_pos = start_pos_world.copy()

            # --- Lógica de movimiento ---
            VISUAL_SPEED = 25.0
            diff = target_pos_world - start_pos_world

            if np.linalg.norm(diff) > 1e-6:
                direction = diff / np.linalg.norm(diff)
            else:
                direction = np.array([0.0, 0.0])

            self.velocity = direction * VISUAL_SPEED

            # --- Lógica de tiempo de vida ---
            self.age = 0.0
            self.lifespan = 2.0  # Segundos de vida máxima

            self._update_screen_pos()

        def _update_screen_pos(self):
            sx, sy = self.renderer._world_to_screen(
                self.world_pos[0], self.world_pos[1])
            self.center_x, self.center_y = sx, sy

        def draw(self):
            # Dibuja un borde para que sea más fácil de ver
            arcade.draw_circle_outline(
                self.center_x, self.center_y, self.radius + 2, arcade.color.WHITE, 2)
            super().draw()

        def on_update(self, delta_time: float = 1/60):
            self.age += delta_time

            # 1. Mover el proyectil
            self.world_pos += self.velocity * delta_time
            self._update_screen_pos()

            # 2. Comprobar condiciones de destrucción

            # --- CORRECCIÓN DE COLISIÓN: Detección dinámica ---
            # Comprobar la colisión con la araña en tiempo real en cada fotograma
            if self.renderer.game_state:
                spider_pos_list = self.renderer.game_state.get('spider_pos')
                spider_health = self.renderer.game_state.get(
                    'spider_health', 0)

                if spider_pos_list and spider_health > 0:
                    spider_world_pos = np.array(spider_pos_list)
                    distance_to_spider = np.linalg.norm(
                        self.world_pos - spider_world_pos)

                    if distance_to_spider < C.SPIDER_RADIUS:
                        self.renderer.trigger_impact_effect(
                            (self.center_x, self.center_y))
                        self.remove_from_sprite_lists()
                        return

            # Tiempo de vida expirado
            if self.age >= self.lifespan:
                self.remove_from_sprite_lists()
                return

            # Fuera de la pantalla (fallback)
            if self.center_y > C.SCREEN_HEIGHT + 20 or self.center_y < -20:
                self.remove_from_sprite_lists()
                return

else:
    Particle = None
    VisualSpit = None

# ------------------------------------------------------


class AntGuardRenderer:
    """
    Renderiza el entorno AntGuard-v1 usando Arcade.
    """

    def __init__(self, render_mode: str):
        self.mode = render_mode

        if not ARCADE_AVAILABLE and render_mode in ["human", "rgb_array"]:
            print("WARNING: Arcade not available. Disabling rendering.")
            self.mode = None

        self.window: arcade.Window | None = None
        self.initialized = False
        self.particle_list: Optional[arcade.SpriteList] = None
        self.projectile_list: Optional[arcade.SpriteList] = None
        self.game_over_sprite = None
        self.impact_shake_timer = 0.0
        self.game_state: Dict[str, Any] | None = None
        self.ant_display_pos = [0.0, 0.0]
        self.randomized_ant_color = (0, 0, 0)
        self.ant_size_multipliers = {
            'head': 1.0, 'thorax': 1.0, 'abdomen': 1.0}
        self.rng_visual = np.random.default_rng()
        self.last_time = 0.0

    def _initialize(self):
        if self.initialized or self.mode is None:
            return

        self.width = C.SCREEN_WIDTH
        self.height = C.WINDOW_HEIGHT

        try:
            self.window = arcade.Window(
                self.width, self.height, "AntGuard-v1: Tactical Defender", visible=(self.mode == "human")
            )
            arcade.set_background_color(C.COLOR_BG_OUTSIDE)
        except Exception as e:
            print(
                f"WARNING: Failed to initialize Arcade window (headless environment?): {e}")
            self.mode = None
            return

        self.particle_list = arcade.SpriteList()
        self.projectile_list = arcade.SpriteList()
        self.initialized = True
        self.last_time = time.time()

    def reset(self):
        if self.particle_list:
            self.particle_list.clear()
        if self.projectile_list:
            self.projectile_list.clear()
        self.game_over_sprite = None
        self.impact_shake_timer = 0.0
        self.last_time = time.time()

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
        y_safe = max(0.01, min(C.WORLD_HEIGHT, y))
        tunnel_height_ratio = 0.9
        game_height_px = C.GAME_HEIGHT * tunnel_height_ratio
        sy = (y_safe / C.WORLD_HEIGHT) * game_height_px + \
            (C.GAME_HEIGHT * (1 - tunnel_height_ratio))
        width_at_y = C.WORLD_WIDTH_BOTTOM + \
            (C.WORLD_WIDTH_TOP - C.WORLD_WIDTH_BOTTOM) * (y_safe / C.WORLD_HEIGHT)

        if width_at_y <= 0:
            return self.width / 2, sy

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

        ant_pos = self.game_state.get('ant_pos', [0.0, 0.0])
        base_sx, base_sy = self._world_to_screen(ant_pos[0], ant_pos[1])
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

        if self.game_state.get('info', {}).get('shot_velocity'):
            ant_base_size = C.SPIDER_RADIUS * 4
            arcade.draw_circle_filled(
                ax, ay, ant_base_size * 0.6, arcade.color.WHITE)

    def _draw_spider(self):
        if not self.game_state or self.game_state.get('spider_health', 0) <= 0:
            return

        spider_pos = self.game_state.get('spider_pos', (0, 0))
        sx, sy = self._world_to_screen(spider_pos[0], spider_pos[1])

        is_impacted = self.impact_shake_timer > 0

        if is_impacted:
            sx += random.uniform(-6, 6)
            sy += random.uniform(-6, 6)
            body_color = (255, 255, 255)
            leg_color = (255, 255, 255)
        else:
            body_color = (40, 10, 50)
            leg_color = (20, 5, 25)

        t = time.time()
        base_size = C.SPIDER_RADIUS * 5
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
            arcade.draw_line(sx, sy, sx + math.cos(math.radians(angle_offset + leg_oscillation)) * leg_length,
                             sy + math.sin(math.radians(angle_offset + leg_oscillation)) * leg_length, leg_color, leg_thickness)
            arcade.draw_line(sx, sy, sx + math.cos(math.radians(180 - angle_offset - leg_oscillation))
                             * leg_length, sy + math.sin(math.radians(180 - angle_offset - leg_oscillation)) * leg_length, leg_color, leg_thickness)

        for i in range(4):
            offset_x = (i - 1.5) * 5
            arcade.draw_circle_filled(
                sx + offset_x, sy + base_size * 0.7, 2, eye_color)

    def _draw_ui(self):
        if not self.game_state:
            return

        color_red = arcade.color.RED if ARCADE_AVAILABLE else (255, 0, 0)
        color_gray = arcade.color.GRAY if ARCADE_AVAILABLE else (128, 128, 128)
        color_lblue = arcade.color.LIGHT_BLUE if ARCADE_AVAILABLE else (
            173, 216, 230)

        health_ratio = self.game_state.get(
            'spider_health', 0) / C.SPIDER_HEALTH_MAX
        arcade.draw_lrbt_rectangle_filled(
            0, self.width * health_ratio, C.WINDOW_HEIGHT - 10, C.WINDOW_HEIGHT, color_red)

        y_start = C.GAME_HEIGHT + C.UI_HEIGHT / 2
        for i in range(C.ANT_ACID_TANK_MAX):
            color = C.COLOR_ACID if i < self.game_state.get(
                'ant_acid_tank', 0) else color_gray
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
                color_lblue
            )

    def _update_visuals(self, delta_time: float):
        """Actualiza timers, procesa eventos y actualiza sprites visuales usando delta_time."""
        if not self.game_state:
            return

        if self.impact_shake_timer > 0:
            self.impact_shake_timer -= delta_time
            if self.impact_shake_timer < 0:
                self.impact_shake_timer = 0.0

        info = self.game_state.get('info', {})

        if info.get('event') == 'spit' and VisualSpit:
            start_pos_world = np.array(
                self.game_state.get('ant_pos', [0.0, 0.0]))

            # --- CORRECCIÓN DE DIRECCIÓN ---
            # Usar el ángulo de la hormiga del estado del juego para determinar la dirección,
            # no el vector de velocidad de la simulación.
            ant_angle_rad = self.game_state.get('ant_angle', 0.0)

            # El ángulo 0 en la simulación es "hacia arriba" (eje Y positivo) en el mundo del juego.
            # Vector de dirección: (-sin(angle), cos(angle)) es incorrecto para un ángulo=0 que apunta a (0,1)
            # La dirección correcta para un ángulo de 0 (apuntando hacia arriba) es (0, 1)
            # Para un ángulo 'a', la dirección es (sin(a), cos(a)) si 0 es (0,1)
            # Pero en Arcade/PyGame, el ángulo 0 suele ser a la derecha (1,0). Y los ángulos crecen en sentido antihorario.
            # El renderizador suma 90 grados, lo que sugiere que el sprite base apunta a la derecha.
            # Si el ángulo del juego 0 es 'arriba', el vector es (0, 1). Si el ángulo es 'a', el vector rotado es (cos(a+pi/2), sin(a+pi/2))
            # que es (-sin(a), cos(a)). Esto parece correcto.
            # El problema debe ser que ant_angle 0 no es (0,1).
            # Si el angulo del juego 0 es 'derecha', el vector es (cos(a), sin(a))
            # Vamos a usar la dirección de la araña como objetivo, que es más robusto

            spider_pos_list = self.game_state.get('spider_pos')
            if spider_pos_list:
                target_pos_world = np.array(spider_pos_list)

                projectile = VisualSpit(
                    start_pos_world=start_pos_world,
                    target_pos_world=target_pos_world,
                    renderer=self
                )
                if self.projectile_list is not None:
                    self.projectile_list.append(projectile)

        if self.projectile_list:
            self.projectile_list.update(delta_time)
        if self.particle_list:
            self.particle_list.update(delta_time)

    def trigger_impact_effect(self, position_screen: Tuple[float, float]):
        """Activa los efectos visuales cuando un proyectil impacta. Usa tiempo real."""

        if self.particle_list and Particle:
            spider_sx, spider_sy = position_screen
            color_white = arcade.color.WHITE if ARCADE_AVAILABLE else (
                255, 255, 255)
            color_ygreen = arcade.color.YELLOW_GREEN if ARCADE_AVAILABLE else (
                154, 205, 50)

            for _ in range(35):
                speed = random.uniform(60, 420)
                angle = random.uniform(0, 2 * math.pi)
                vel = (speed * math.cos(angle), speed * math.sin(angle))
                lifespan = 0.6
                color = random.choice(
                    [color_white, C.COLOR_ACID, color_ygreen])
                p = Particle(radius=random.uniform(2, 5), color=color, position=(
                    spider_sx, spider_sy), velocity=vel, lifespan=lifespan)
                self.particle_list.append(p)

        self.impact_shake_timer = 0.5

    def update(self, state: Dict[str, Any]):
        if self.mode not in ["human", "rgb_array"]:
            return None

        if not self.initialized:
            self._initialize()

        if not self.window:
            return None

        current_time = time.time()
        delta_time = min(current_time - self.last_time, 1/15.0)
        self.last_time = current_time

        self.game_state = state

        self._update_visuals(delta_time)

        try:
            if self.mode == "human":
                self.window.dispatch_events()

            self.window.switch_to()
            self.window.clear()
        except Exception:
            return None

        self._draw_background()

        self._draw_ant()
        self._draw_spider()

        if self.particle_list:
            self.particle_list.draw()
        if self.projectile_list:
            self.projectile_list.draw()

        self._draw_ui()

        if self.game_state and self.game_state.get('game_over', False):
            msg = "VICTORIA" if self.game_state.get(
                'spider_health', 0) <= 0 else "DERROTA"
            color_white = arcade.color.WHITE if ARCADE_AVAILABLE else (
                255, 255, 255)
            arcade.draw_text(msg, self.width/2, self.height/2,
                             color_white, 40, anchor_x="center")

        if self.mode == "human":
            # print(f"🎬 Proyectiles en pantalla: {len(self.projectile_list)}")
            self.window.flip()

        return None
