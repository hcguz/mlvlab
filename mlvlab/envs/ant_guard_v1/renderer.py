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
        """Partícula mejorada para efectos visuales (Requisito 6.2)."""

        def __init__(self, radius: float, color: Tuple, position: Tuple, velocity: Tuple, lifespan: float):
            super().__init__(radius=int(radius), color=color)
            self.center_x, self.center_y = position
            self.change_x, self.change_y = velocity
            self.lifespan = lifespan
            self.max_lifespan = lifespan

        def update(self):
            super().update()
            self.lifespan -= 1

            # Efecto de desvanecimiento (Fade out) más suave
            self.alpha = int(255 * (self.lifespan / self.max_lifespan)**0.5)

            # Efecto de encogimiento (Shrink)
            if self.lifespan < self.max_lifespan * 0.5:
                self.scale *= 0.94

            if self.lifespan <= 0:
                self.remove_from_sprite_lists()

    # --- NUEVA CLASE: VisualProjectile (Requisito 6.2) ---
    class VisualProjectile(arcade.SpriteCircle):
        """
        Proyectil visual que se mueve en coordenadas del mundo para una perspectiva correcta.
        Desacoplado de la lógica del juego (que es instantánea).
        """

        def __init__(self, start_pos_world: np.ndarray, velocity_world: np.ndarray,
                     target_pos_world: Optional[np.ndarray], renderer: 'AntGuardRenderer'):

            # Apariencia del proyectil principal
            super().__init__(radius=6, color=C.COLOR_ACID)
            self.renderer = renderer

            # Coordenadas y movimiento en el mundo
            self.world_pos = start_pos_world.copy()
            self.velocity = velocity_world
            self.target_pos = target_pos_world
            self.speed = np.linalg.norm(self.velocity)

            # Cálculo de la distancia objetivo
            if self.target_pos is not None:
                diff = self.target_pos - self.world_pos
                self.target_distance = np.linalg.norm(diff)
            else:
                self.target_distance = float('inf')

            self.distance_traveled = 0

            # Establecer posición inicial en pantalla
            self._update_screen_pos()

        def _update_screen_pos(self):
            sx, sy = self.renderer._world_to_screen(
                self.world_pos[0], self.world_pos[1])
            self.center_x, self.center_y = sx, sy

        def update(self):
            # 1. Mover (Coordenadas del mundo)
            self.world_pos += self.velocity
            self.distance_traveled += self.speed

            # 2. Comprobar si ha alcanzado el objetivo (Impacto visual retardado)
            if self.distance_traveled >= self.target_distance:
                if self.target_pos is not None:
                    # Asegurar que la posición final sea exacta
                    self.world_pos = self.target_pos.copy()
                    self._update_screen_pos()
                    # Activar el efecto de impacto en el renderer en la posición final
                    self.renderer.trigger_impact_effect(
                        (self.center_x, self.center_y))
                self.remove_from_sprite_lists()
                return

            # 3. Comprobar límites (Coordenadas del mundo) para misses
            # Límites verticales
            if self.world_pos[1] > C.WORLD_HEIGHT * 1.05 or self.world_pos[1] < -5:
                self.remove_from_sprite_lists()
                return

            # Límites laterales (Cono)
            safe_y = max(0.01, self.world_pos[1])
            width_at_y = C.WORLD_WIDTH_BOTTOM + \
                (C.WORLD_WIDTH_TOP - C.WORLD_WIDTH_BOTTOM) * \
                (safe_y / C.WORLD_HEIGHT)
            max_x = width_at_y / 2

            if abs(self.world_pos[0]) > max_x + 2:  # Pequeña tolerancia
                self.remove_from_sprite_lists()
                return

            # 4. Actualizar posición en pantalla
            self._update_screen_pos()

            # 5. Generar rastro de partículas (Efecto "chorro")
            self._generate_trail_particles()

        def _generate_trail_particles(self):
            if not self.renderer.particle_list:
                return

            for _ in range(3):  # Densidad del rastro
                # Velocidad de dispersión aleatoria (en pantalla)
                speed = random.uniform(0.5, 2.5)
                angle = random.uniform(0, 2 * math.pi)

                # Ligera tendencia a quedarse atrás (basado en la dirección Y del movimiento)
                vy_dir = -np.sign(self.velocity[1]
                                  ) if self.velocity[1] != 0 else 0

                vel = (speed * math.cos(angle),
                       speed * math.sin(angle) + vy_dir * 1.0)

                p = Particle(radius=random.uniform(2, 4), color=C.COLOR_ACID,
                             position=(self.center_x,
                                       self.center_y), velocity=vel,
                             lifespan=random.randint(15, 35))
                self.renderer.particle_list.append(p)
else:
    Particle = None
    VisualProjectile = None

# ------------------------------------------------------


class AntGuardRenderer:
    """
    Renderiza el entorno AntGuard-v1 usando Arcade.
    """

    def __init__(self, render_mode: str):
        self.mode = render_mode

        # Verificar disponibilidad de Arcade
        if not ARCADE_AVAILABLE and render_mode in ["human", "rgb_array"]:
            print("WARNING: Arcade not available. Disabling rendering.")
            self.mode = None

        self.window: arcade.Window | None = None
        self.initialized = False
        self.particle_list: Optional[arcade.SpriteList] = None
        self.projectile_list: Optional[arcade.SpriteList] = None
        self.game_over_sprite = None
        # NUEVO: Timer para efecto de impacto retardado
        self.impact_shake_timer = 0

        self.game_state: Dict[str, Any] | None = None

        self.ant_display_pos = [0.0, 0.0]
        self.randomized_ant_color = (0, 0, 0)
        self.ant_size_multipliers = {
            'head': 1.0, 'thorax': 1.0, 'abdomen': 1.0}
        self.rng_visual = np.random.default_rng()
        self.last_time = 0

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
        self.impact_shake_timer = 0

        # Código de aleatorización de la hormiga
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
        # Se añade robustez limitando Y para evitar distorsiones extremas o divisiones por cero
        y_safe = max(0.01, min(C.WORLD_HEIGHT, y))

        tunnel_height_ratio = 0.9
        game_height_px = C.GAME_HEIGHT * tunnel_height_ratio

        # Usamos y_safe para el cálculo visual
        sy = (y_safe / C.WORLD_HEIGHT) * game_height_px + \
            (C.GAME_HEIGHT * (1 - tunnel_height_ratio))

        width_at_y = C.WORLD_WIDTH_BOTTOM + \
            (C.WORLD_WIDTH_TOP - C.WORLD_WIDTH_BOTTOM) * (y_safe / C.WORLD_HEIGHT)

        # Protección contra división por cero (aunque y_safe >= 0.01 debería evitarlo)
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

        # Usamos la posición almacenada en el estado (que es [0, 0])
        ant_pos = self.game_state.get('ant_pos', [0.0, 0.0])
        base_sx, base_sy = self._world_to_screen(ant_pos[0], ant_pos[1])

        # ant_angle=0 es arriba. +90 grados para que el dibujo (que asume 0=derecha) apunte arriba.
        angle_deg = math.degrees(self.game_state.get('ant_angle', 0)) + 90

        self.ant_display_pos[0] = base_sx
        self.ant_display_pos[1] = base_sy

        ax, ay = self.ant_display_pos
        t = time.time()

        # ... (El código de dibujo detallado de la hormiga permanece igual) ...
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

        # Animación de disparo (fogonazo instantáneo)
        # Se activa si se ha disparado en este frame (verificando si hay velocidad de disparo en info)
        if self.game_state.get('info', {}).get('shot_velocity'):
            # Fogonazo blanco rápido (Requisito 6.1)
            arcade.draw_circle_filled(
                ax, ay, ant_base_size * 0.6, arcade.color.WHITE)

    def _draw_spider(self):
        if not self.game_state or self.game_state.get('spider_health', 0) <= 0:
            return

        spider_pos = self.game_state.get('spider_pos', (0, 0))
        sx, sy = self._world_to_screen(spider_pos[0], spider_pos[1])

        # --- MODIFICACIÓN: Efecto de impacto retardado (Requisito 6.3) ---
        # El impacto visual ahora depende del timer, no del evento instantáneo.
        is_impacted = self.impact_shake_timer > 0

        if is_impacted:
            # Aplicar temblor
            sx += random.uniform(-6, 6)
            sy += random.uniform(-6, 6)
            # Parpadear en blanco
            body_color = (255, 255, 255)
            leg_color = (255, 255, 255)
        else:
            # Colores normales
            body_color = (40, 10, 50)
            leg_color = (20, 5, 25)

        t = time.time()
        base_size = C.SPIDER_RADIUS * 5
        eye_color = (255, 0, 50)

        # Dibujo del cuerpo de la araña
        abdomen_w, abdomen_h = base_size * 1.2, base_size * 1.5
        head_w, head_h = base_size, base_size

        arcade.draw_ellipse_filled(
            sx, sy - base_size * 0.4, abdomen_w, abdomen_h, body_color)
        arcade.draw_ellipse_filled(
            sx, sy + base_size * 0.5, head_w, head_h, body_color)

        # Dibujo de las patas
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

        # Dibujo de los ojos
        for i in range(4):
            offset_x = (i - 1.5) * 5
            arcade.draw_circle_filled(
                sx + offset_x, sy + base_size * 0.7, 2, eye_color)

    def _draw_ui(self):
        if not self.game_state:
            return

        # Definir colores con fallback
        color_red = arcade.color.RED if ARCADE_AVAILABLE else (255, 0, 0)
        color_gray = arcade.color.GRAY if ARCADE_AVAILABLE else (128, 128, 128)
        color_lblue = arcade.color.LIGHT_BLUE if ARCADE_AVAILABLE else (
            173, 216, 230)

        # Barra de vida de la araña
        health_ratio = self.game_state.get(
            'spider_health', 0) / C.SPIDER_HEALTH_MAX
        arcade.draw_lrbt_rectangle_filled(
            0, self.width * health_ratio, C.WINDOW_HEIGHT - 10, C.WINDOW_HEIGHT, color_red)

        # Indicador de ácido
        y_start = C.GAME_HEIGHT + C.UI_HEIGHT / 2
        for i in range(C.ANT_ACID_TANK_MAX):
            color = C.COLOR_ACID if i < self.game_state.get(
                'ant_acid_tank', 0) else color_gray
            arcade.draw_circle_filled(30 + i * 25, y_start, 10, color)

        # Barra de recarga (Cooldown)
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

    # --- NUEVO: Métodos para gestionar efectos visuales ---

    def _update_visuals(self):
        """Actualiza timers, procesa eventos y actualiza sprites visuales."""
        if not self.game_state:
            return

        # 0. Actualizar timers
        if self.impact_shake_timer > 0:
            self.impact_shake_timer -= 1

        # 1. Procesar eventos del juego (Crear nuevos sprites)
        info = self.game_state.get('info', {})

        # 1.1. Manejar Evento de Disparo (Creación de nuevo proyectil)
        # Se comprueba si hay datos de velocidad, lo que indica un disparo este frame.
        shot_velocity_list = info.get('shot_velocity')

        if shot_velocity_list and VisualProjectile:
            # Obtener datos del estado del juego (convertir listas a numpy arrays para operaciones)
            start_pos_world = np.array(
                self.game_state.get('ant_pos', [0.0, 0.0]))
            velocity_world = np.array(shot_velocity_list)

            # El target_pos puede ser None si fue un miss
            target_pos_list = self.game_state.get('shot_target_pos')
            target_pos_world = np.array(
                target_pos_list) if target_pos_list else None

            # Crear el proyectil visual
            projectile = VisualProjectile(
                start_pos_world=start_pos_world,
                velocity_world=velocity_world,
                target_pos_world=target_pos_world,
                renderer=self
            )
            if self.projectile_list:
                self.projectile_list.append(projectile)

        # 2. Actualizar sprites existentes
        if self.projectile_list:
            self.projectile_list.update()
        if self.particle_list:
            self.particle_list.update()

    def trigger_impact_effect(self, position_screen: Tuple[float, float]):
        """Activa los efectos visuales cuando un proyectil impacta el objetivo (Requisito 6.3)."""

        # 1. Partículas de impacto (Explosión)
        if self.particle_list and Particle:
            spider_sx, spider_sy = position_screen
            color_white = arcade.color.WHITE if ARCADE_AVAILABLE else (
                255, 255, 255)
            color_ygreen = arcade.color.YELLOW_GREEN if ARCADE_AVAILABLE else (
                154, 205, 50)

            for _ in range(35):
                # Explosión radial energética
                speed = random.uniform(1, 7)
                angle = random.uniform(0, 2 * math.pi)
                vel = (speed * math.cos(angle), speed * math.sin(angle))

                # Color blanco o verde brillante
                color = random.choice(
                    [color_white, C.COLOR_ACID, color_ygreen])
                p = Particle(radius=random.uniform(2, 5), color=color, position=(
                    spider_sx, spider_sy), velocity=vel, lifespan=35)
                self.particle_list.append(p)

        # 2. Iniciar animación de temblor y parpadeo de la araña
        self.impact_shake_timer = 15  # Duración del efecto (0.5s a 30fps)

    def update(self, state: Dict[str, Any]):
        if self.mode not in ["human", "rgb_array"]:
            print(f"DEBUG: Renderer mode is {self.mode}, returning None")
            return None

        if not self.initialized:
            print("DEBUG: Initializing renderer...")
            self._initialize()

        if not self.window:
            print("DEBUG: No window available, returning None")
            return None

        self.game_state = state

        # Actualizar todos los elementos visuales (proyectiles, partículas, timers)
        self._update_visuals()

        try:
            # --- MEJORA DE COMPATIBILIDAD CON WRAPPERS ---
            # Procesar eventos para evitar que la ventana se congele en modo 'human'.
            if self.mode == "human":
                self.window.dispatch_events()

            self.window.switch_to()
            self.window.clear()
        except Exception:
            # Manejo de excepción si la ventana se cierra inesperadamente
            return None

        # Dibujar la escena
        self._draw_background()
        self._draw_ant()
        self._draw_spider()

        # Dibujar sprites (partículas debajo de proyectiles)
        if self.particle_list:
            self.particle_list.draw()
        if self.projectile_list:
            self.projectile_list.draw()

        self._draw_ui()

        # Mensaje de Game Over
        if self.game_state and self.game_state.get('game_over', False):
            msg = "VICTORIA" if self.game_state.get(
                'spider_health', 0) <= 0 else "DERROTA"
            color_white = arcade.color.WHITE if ARCADE_AVAILABLE else (
                255, 255, 255)
            arcade.draw_text(msg, self.width/2, self.height/2,
                             color_white, 40, anchor_x="center")

        # Finalizar el renderizado y devolver el resultado
        if self.mode == "rgb_array":
            try:
                # Capturar la imagen directamente (como hace AntMaze)
                image_rgba = arcade.get_image()
                image_rgb = image_rgba.convert("RGB")
                result = np.array(image_rgb)
                # print(f"DEBUG: Returning rgb_array with shape {result.shape}")
                return result
            except Exception as e:
                # print(f"Error capturando rgb_array: {e}")
                fallback = np.zeros(
                    (self.height, self.width, 3), dtype=np.uint8)
                # print( f"DEBUG: Returning fallback array with shape {fallback.shape}")
                return fallback

        elif self.mode == "human":
            # Mostrar el buffer en pantalla
            self.window.flip()
            # print("DEBUG: Human mode, returning None")

        # print("DEBUG: End of update, returning None")
        return None
