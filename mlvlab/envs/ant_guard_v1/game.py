# game.py
import numpy as np
import math
from typing import Optional, Dict, Any

try:
    from .constants import C
except ImportError:
    # Fallback para ejecución directa
    from constants import C


class AntGuardGame:
    """
    Lógica central del entorno AntGuard-v1.
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self.np_random = np.random.default_rng(seed)
        self.ant_pos = np.array([0.0, 0.0], dtype=np.float32)
        # Almacena la posición del impacto (para visualización retardada)
        self.shot_target_pos: Optional[np.ndarray] = None
        # NUEVO: Delta time fijo para la lógica del juego
        self.dt = 1.0 / C.LOGIC_FPS
        self.reset()

    def reset(self):
        self.current_step = 0
        self.game_over = False
        self.info = self._base_info()
        self.ant_angle = 0.0
        self.ant_acid_tank = C.ANT_ACID_TANK_MAX
        self.cooldown_timer = 0
        self.spider_health = C.SPIDER_HEALTH_MAX
        self.shot_target_pos = None  # Resetear visualización

        initial_x = self.np_random.uniform(-C.WORLD_WIDTH_TOP /
                                           3, C.WORLD_WIDTH_TOP / 3)
        self.spider_pos = np.array(
            [initial_x, C.WORLD_HEIGHT], dtype=np.float32)

    def _base_info(self) -> Dict[str, Any]:
        # Se añade shot_velocity para que el renderer pueda instanciar el proyectil visual
        return {'event': 'none', 'hit_registered': False, 'shot_velocity': None}

    def get_state(self) -> Dict[str, Any]:
        # Devuelve el estado completo para el renderer
        # Se convierten arrays a listas para mayor compatibilidad (e.g. serialización)
        return {
            "ant_angle": self.ant_angle,
            "ant_acid_tank": self.ant_acid_tank,
            "ant_pos": self.ant_pos.tolist(),
            "spider_health": self.spider_health,
            "spider_pos": self.spider_pos.tolist(),
            # Posición objetivo del disparo (si hubo impacto en este step)
            "shot_target_pos": self.shot_target_pos.tolist() if self.shot_target_pos is not None else None,
            "cooldown_timer": self.cooldown_timer,
            "game_over": self.game_over,
            "info": self.info
        }

    def _calculate_observation(self) -> Dict[str, np.ndarray]:
        # ... (Permanece igual, omitido por brevedad) ...
        if self.spider_health <= 0:
            dist_angle = np.array([0, 0], dtype=np.float32)
        else:
            diff = self.spider_pos - self.ant_pos
            dist = np.linalg.norm(diff)
            angle_to_spider = math.atan2(diff[1], diff[0])
            relative_angle = (self.ant_angle - (angle_to_spider - math.pi / 2))
            relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi
            dist_angle = np.array([dist, relative_angle], dtype=np.float32)

        vitals = np.array([
            self.spider_health,
            self.ant_acid_tank,
            self.cooldown_timer
        ], dtype=np.float32)

        return {"distance": dist_angle, "vitals": vitals}

    def _handle_shot(self) -> int:
        self.ant_acid_tank -= 1
        self.cooldown_timer = C.SPIT_COOLDOWN_FRAMES_MAX
        self.info['event'] = 'spit'

        # 1. Calcular ángulo de disparo (respecto al eje Y positivo)
        ant_fire_angle = math.pi / 2 - self.ant_angle

        # 2. Calcular velocidad del proyectil (Ahora en unidades/segundo)
        vx = math.cos(ant_fire_angle) * C.VISUAL_PROJECTILE_SPEED
        vy = math.sin(ant_fire_angle) * C.VISUAL_PROJECTILE_SPEED
        projectile_velocity = np.array([vx, vy])
        self.info['shot_velocity'] = [vx, vy]

        # 3. Simular trayectoria del proyectil vs movimiento de la araña
        hit_result = self._simulate_projectile_trajectory(projectile_velocity)

        if hit_result['hit']:
            self.spider_health -= 1
            self.info['event'] = 'hit'
            self.info['hit_registered'] = True
            self.shot_target_pos = hit_result['impact_pos']

            if self.spider_health <= 0:
                self.info['event'] = 'spider_killed'
                return C.REWARD_HIT + C.REWARD_KILL
            return C.REWARD_HIT
        else:
            # Miss
            self.shot_target_pos = hit_result['impact_pos']
            return C.REWARD_MISS

    def _simulate_projectile_trajectory(self, projectile_velocity: np.ndarray) -> dict:
        """
        Simula la trayectoria usando velocidades en unidades/s y un dt fino.
        """
        # Posiciones iniciales
        projectile_pos = self.ant_pos.copy()
        spider_pos = self.spider_pos.copy()

        # Simular paso a paso
        max_simulation_steps = 1000
        # Usamos una resolución fina (120 Hz) para la simulación de colisión.
        dt = 1.0 / 120.0

        for step in range(max_simulation_steps):
            # Mover proyectil (Velocity está en unidades/s)
            projectile_pos += projectile_velocity * dt

            # Mover araña (SPIDER_SPEED está en unidades/s)
            spider_pos = self._simulate_spider_movement_step(spider_pos, dt)

            # Verificar colisión
            distance = np.linalg.norm(projectile_pos - spider_pos)
            if distance <= C.SPIDER_RADIUS:
                return {
                    'hit': True,
                    'impact_pos': spider_pos.copy(),
                }

            # Verificar si el proyectil sale del área de juego
            if self._is_out_of_bounds(projectile_pos):
                return {
                    'hit': False,
                    'impact_pos': projectile_pos.copy(),
                }

        return {
            'hit': False,
            'impact_pos': projectile_pos.copy(),
        }

    def _simulate_spider_movement_step(self, spider_pos: np.ndarray, dt: float) -> np.ndarray:
        """Simula un paso del movimiento de la araña usando dt."""
        direction_to_ant = self.ant_pos - spider_pos
        norm = np.linalg.norm(direction_to_ant)
        if norm > 0:
            direction_to_ant /= norm

        # Movimiento en Zigzag
        zigzag_offset = math.sin(
            self.current_step * C.ZIGZAG_FREQUENCY) * (C.WORLD_WIDTH_TOP / 4)
        perpendicular_dir = np.array(
            [-direction_to_ant[1], direction_to_ant[0]])

        final_direction = direction_to_ant + perpendicular_dir * zigzag_offset
        norm_final = np.linalg.norm(final_direction)
        if norm_final > 0:
            final_direction /= norm_final

        # C.SPIDER_SPEED está en unidades/s.
        new_spider_pos = spider_pos + final_direction * C.SPIDER_SPEED * dt

        # Aplicar límites del túnel
        new_x, new_y = new_spider_pos
        safe_y = max(0, new_y)
        max_x_at_y = (C.WORLD_WIDTH_BOTTOM + (C.WORLD_WIDTH_TOP -
                      C.WORLD_WIDTH_BOTTOM) * (safe_y / C.WORLD_HEIGHT)) / 2
        new_spider_pos[0] = np.clip(new_x, -max_x_at_y, max_x_at_y)

        return new_spider_pos

    def _is_out_of_bounds(self, pos: np.ndarray) -> bool:
        # ... (Permanece igual, omitido por brevedad) ...
        x, y = pos

        # Límites verticales
        if y > C.WORLD_HEIGHT * 1.1 or y < -10:
            return True

        # Límites laterales (cono del túnel)
        if y < 0:
            return False  # Dentro del área inferior

        # Clampeamos Y para evitar que el ancho sea mayor que WORLD_WIDTH_TOP
        y_clamped = min(y, C.WORLD_HEIGHT)

        width_at_y = C.WORLD_WIDTH_BOTTOM + \
            (C.WORLD_WIDTH_TOP - C.WORLD_WIDTH_BOTTOM) * \
            (y_clamped / C.WORLD_HEIGHT)
        max_x = width_at_y / 2

        return abs(x) > max_x + 5

    def _update_spider_movement(self):
        direction_to_ant = self.ant_pos - self.spider_pos
        norm = np.linalg.norm(direction_to_ant)
        if norm > 0:
            direction_to_ant /= norm

        # Movimiento en Zigzag
        zigzag_offset = math.sin(
            self.current_step * C.ZIGZAG_FREQUENCY) * (C.WORLD_WIDTH_TOP / 4)
        perpendicular_dir = np.array(
            [-direction_to_ant[1], direction_to_ant[0]])

        final_direction = direction_to_ant + perpendicular_dir * zigzag_offset
        norm_final = np.linalg.norm(final_direction)
        if norm_final > 0:
            final_direction /= norm_final

        # ACTUALIZADO: Usar self.dt (el dt de la lógica) para movimiento basado en tiempo
        self.spider_pos += final_direction * C.SPIDER_SPEED * self.dt

        # --- CORRECCIÓN DE LÍMITES ---
        new_x, new_y = self.spider_pos
        safe_y = max(0, new_y)
        max_x_at_y = (C.WORLD_WIDTH_BOTTOM + (C.WORLD_WIDTH_TOP -
                      C.WORLD_WIDTH_BOTTOM) * (safe_y / C.WORLD_HEIGHT)) / 2
        self.spider_pos[0] = np.clip(new_x, -max_x_at_y, max_x_at_y)

    def update(self, action: int) -> int:
        self.current_step += 1
        # Importante: Resetear info y shot_target_pos antes de ejecutar acciones del paso
        self.info = self._base_info()
        # CORRECCIÓN DE SINCRONIZACIÓN: Reseteamos el target al inicio del step.
        # El renderer ya habrá leído el valor del step anterior si fue necesario.
        self.shot_target_pos = None

        reward = C.REWARD_STEP

        # Actualizar temporizador
        self.cooldown_timer = max(0, self.cooldown_timer - 1)

        # Acciones del agente
        if action == 1:  # Rotate Left (CCW)
            # ACTUALIZADO: Usar self.dt para rotación basada en tiempo
            self.ant_angle += C.ROTATION_SPEED * self.dt
        elif action == 2:  # Rotate Right (CW)
            # ACTUALIZADO: Usar self.dt para rotación basada en tiempo
            self.ant_angle -= C.ROTATION_SPEED * self.dt
        elif action == 3:  # Spit Acid
            if self.cooldown_timer == 0 and self.ant_acid_tank > 0:
                reward += self._handle_shot()

        # Normalizar ángulo de la hormiga
        self.ant_angle = (self.ant_angle + np.pi) % (2 * np.pi) - np.pi

        # Movimiento del enemigo
        if self.spider_health > 0:
            self._update_spider_movement()

        # Condiciones de fin de episodio
        if self.spider_health <= 0:
            self.game_over = True
        elif self.spider_pos[1] <= 0 or np.linalg.norm(self.spider_pos - self.ant_pos) < C.SPIDER_RADIUS:
            if self.spider_health > 0:
                reward += C.REWARD_LOSE
            self.game_over = True

        # CORRECCIÓN DE SINCRONIZACIÓN: Eliminado el reseteo al final del update.
        # if self.shot_target_pos is not None:
        #     self.shot_target_pos = None

        return reward
