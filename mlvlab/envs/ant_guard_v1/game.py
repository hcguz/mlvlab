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
        self.reset()

    def reset(self):
        self.current_step = 0
        self.game_over = False
        self.info = self._base_info()
        self.ant_angle = 0.0
        self.ant_acid_tank = C.ANT_ACID_TANK_MAX
        self.cooldown_timer = 0
        self.spider_health = C.SPIDER_HEALTH_MAX

        initial_x = self.np_random.uniform(-C.WORLD_WIDTH_TOP /
                                           3, C.WORLD_WIDTH_TOP / 3)
        self.spider_pos = np.array(
            [initial_x, C.WORLD_HEIGHT], dtype=np.float32)

    def _base_info(self) -> Dict[str, Any]:
        return {'event': 'none', 'hit_registered': False}

    def get_state(self) -> Dict[str, Any]:
        return {
            "ant_angle": self.ant_angle,
            "ant_acid_tank": self.ant_acid_tank,
            "spider_health": self.spider_health,
            "spider_pos": self.spider_pos,
            "cooldown_timer": self.cooldown_timer,
            "game_over": self.game_over,
            "info": self.info
        }

    def _calculate_observation(self) -> Dict[str, np.ndarray]:
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

        diff = self.spider_pos - self.ant_pos
        angle_to_spider = math.atan2(diff[1], diff[0])
        ant_fire_angle = -self.ant_angle + math.pi / 2

        angle_diff = abs((ant_fire_angle - angle_to_spider +
                         np.pi) % (2 * np.pi) - np.pi)

        hit_threshold = math.atan(C.SPIDER_RADIUS / np.linalg.norm(diff))

        if angle_diff <= hit_threshold:
            self.spider_health -= 1
            self.info['event'] = 'hit'
            self.info['hit_registered'] = True
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
        # Se añade esta sección para asegurar que la araña no se salga del túnel.
        new_x, new_y = self.spider_pos
        # Calcula el ancho máximo del túnel en la nueva posición Y de la araña.
        max_x_at_y = (C.WORLD_WIDTH_BOTTOM + (C.WORLD_WIDTH_TOP -
                      C.WORLD_WIDTH_BOTTOM) * (new_y / C.WORLD_HEIGHT)) / 2
        # Limita la posición X de la araña a ese ancho.
        self.spider_pos[0] = np.clip(new_x, -max_x_at_y, max_x_at_y)

    def update(self, action: int) -> int:
        self.current_step += 1
        self.info = self._base_info()
        reward = C.REWARD_STEP

        # --- CORRECCIÓN DEL DISPARO ---
        # Se añade esta línea faltante para que el temporizador de recarga disminuya.
        self.cooldown_timer = max(0, self.cooldown_timer - 1)

        if action == 1:
            self.ant_angle += C.ROTATION_SPEED
        elif action == 2:
            self.ant_angle -= C.ROTATION_SPEED
        elif action == 3:
            if self.cooldown_timer == 0 and self.ant_acid_tank > 0:
                reward += self._handle_shot()

        self.ant_angle = (self.ant_angle + np.pi) % (2 * np.pi) - np.pi

        if self.spider_health > 0:
            self._update_spider_movement()

        if self.spider_health <= 0:
            self.game_over = True
        elif self.spider_pos[1] <= 0 or np.linalg.norm(self.spider_pos - self.ant_pos) < C.SPIDER_RADIUS:
            if self.spider_health > 0:
                reward += C.REWARD_LOSE
            self.game_over = True

        return reward
