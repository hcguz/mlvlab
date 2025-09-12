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
        # NUEVO: Almacena la posición del impacto (para visualización retardada)
        self.shot_target_pos: Optional[np.ndarray] = None
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
            # NUEVO: Posición objetivo del disparo (si hubo impacto)
            "shot_target_pos": self.shot_target_pos.tolist() if self.shot_target_pos is not None else None,
            "cooldown_timer": self.cooldown_timer,
            "game_over": self.game_over,
            "info": self.info
        }

    def _calculate_observation(self) -> Dict[str, np.ndarray]:
        # La observación del agente permanece inalterada (Compatibilidad con Wrappers)
        if self.spider_health <= 0:
            dist_angle = np.array([0, 0], dtype=np.float32)
        else:
            diff = self.spider_pos - self.ant_pos
            dist = np.linalg.norm(diff)
            angle_to_spider = math.atan2(diff[1], diff[0])
            # Ángulo relativo: 0 es recto, positivo es izquierda (CCW), negativo es derecha (CW)
            relative_angle = (self.ant_angle - (angle_to_spider - math.pi / 2))
            # Normalizar el ángulo al rango [-pi, pi]
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
        self.shot_target_pos = None  # Resetear objetivo al disparar

        # 1. Calcular ángulo de disparo (respecto al eje Y positivo)
        # ant_angle=0 es arriba. Positivo es CCW (izquierda).
        # Queremos el ángulo matemático estándar (respecto al eje X positivo).
        # Eje Y positivo = pi/2. Ángulo matemático = pi/2 - ant_angle.
        ant_fire_angle = math.pi / 2 - self.ant_angle

        # 2. Calcular y almacenar velocidad para el proyectil visual (Requisito 6.2)
        vx = math.cos(ant_fire_angle) * C.VISUAL_PROJECTILE_SPEED
        vy = math.sin(ant_fire_angle) * C.VISUAL_PROJECTILE_SPEED
        # Se almacena como lista para compatibilidad
        self.info['shot_velocity'] = [vx, vy]

        # 3. Cálculo de impacto instantáneo (Requisito 4.3)
        diff = self.spider_pos - self.ant_pos
        dist = np.linalg.norm(diff)
        angle_to_spider = math.atan2(diff[1], diff[0])

        # Calcular la diferencia angular y normalizarla
        angle_diff = abs((ant_fire_angle - angle_to_spider +
                         np.pi) % (2 * np.pi) - np.pi)

        # El umbral de impacto depende de la distancia (trigonometría básica)
        # Si la distancia es 0, el impacto es seguro.
        hit_threshold = math.atan(
            C.SPIDER_RADIUS / dist) if dist > 0 else np.pi

        if angle_diff <= hit_threshold:
            self.spider_health -= 1
            self.info['event'] = 'hit'
            self.info['hit_registered'] = True

            # Guardar la posición exacta del impacto (en coordenadas del mundo)
            self.shot_target_pos = self.spider_pos.copy()

            if self.spider_health <= 0:
                self.info['event'] = 'spider_killed'
                return C.REWARD_HIT + C.REWARD_KILL
            return C.REWARD_HIT
        else:
            return C.REWARD_MISS

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

        self.spider_pos += final_direction * C.SPIDER_SPEED

        # --- CORRECCIÓN DE LÍMITES ---
        new_x, new_y = self.spider_pos
        # Asegurarse que Y no sea negativo para el cálculo del ancho del túnel
        safe_y = max(0, new_y)
        max_x_at_y = (C.WORLD_WIDTH_BOTTOM + (C.WORLD_WIDTH_TOP -
                      C.WORLD_WIDTH_BOTTOM) * (safe_y / C.WORLD_HEIGHT)) / 2
        self.spider_pos[0] = np.clip(new_x, -max_x_at_y, max_x_at_y)

    def update(self, action: int) -> int:
        self.current_step += 1
        # Importante: Resetear info antes de ejecutar acciones del paso
        self.info = self._base_info()
        reward = C.REWARD_STEP

        # Actualizar temporizador
        self.cooldown_timer = max(0, self.cooldown_timer - 1)

        # Acciones del agente
        if action == 1:  # Rotate Left (CCW)
            self.ant_angle += C.ROTATION_SPEED
        elif action == 2:  # Rotate Right (CW)
            self.ant_angle -= C.ROTATION_SPEED
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

        return reward
