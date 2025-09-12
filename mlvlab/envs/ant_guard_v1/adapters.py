import gymnasium as gym
import numpy as np
from gymnasium import spaces

try:
    from .constants import C
except ImportError:
    # Fallback para ejecución directa
    from constants import C


class TacticalWrapper(gym.ObservationWrapper):
    """
    Wrapper para AntGuard-v1 que discretiza el espacio de observación complejo
    en un único entero para Q-Learning Tabular (Requisito 7).

    Total states = 4 (dist) * 8 (ang) * 3 (vida 1-3) * 6 (ácido 0-5) * 2 (recarga) = 1152.
    """

    def __init__(self, env):
        super().__init__(env)

        # Parámetros de discretización
        self.num_dist_bins = C.WRAPPER_NUM_DIST_BINS
        self.num_angle_bins = C.WRAPPER_NUM_ANGLE_BINS

        # Rangos para el cálculo del ID:
        # Health: 0 a (MAX_HEALTH-1). Rango = MAX_HEALTH
        self.health_range = C.SPIDER_HEALTH_MAX
        # Acid: 0 a MAX_ACID. Rango = MAX_ACID + 1
        self.acid_range = C.ANT_ACID_TANK_MAX + 1
        self.cooldown_states = 2

        total_states = (self.num_dist_bins *
                        self.num_angle_bins *
                        self.health_range *
                        self.acid_range *
                        self.cooldown_states)

        self.observation_space = spaces.Discrete(total_states)

        self.max_dist = C.MAX_DIST

        # Pre-calcular los bins para eficiencia
        # Excluimos el primer (0) y último (MAX) borde para obtener N bins.
        self.dist_bins = np.linspace(
            0, self.max_dist, self.num_dist_bins + 1)[1:-1]
        self.angle_bins = np.linspace(-np.pi, np.pi,
                                      self.num_angle_bins + 1)[1:-1]

    def observation(self, obs):
        # obs = {'distance': [dist, angle], 'vitals': [health, acid, cd]}
        dist, angle = obs['distance']
        spider_health, ant_acid, cooldown = obs['vitals']

        # 1. Discretizar las variables continuas
        dist_idx = np.digitize(dist, bins=self.dist_bins)
        angle_idx = np.digitize(angle, bins=self.angle_bins)

        # Asegurar límites
        dist_idx = max(0, min(dist_idx, self.num_dist_bins - 1))
        angle_idx = max(0, min(angle_idx, self.num_angle_bins - 1))

        # 2. Normalizar las variables discretas

        # Vida: Índice 0 a (MAX_HEALTH-1). Mapeamos [1, 2, 3] a [0, 1, 2].
        # Si vida=0 (muerta), usamos índice 0 por seguridad, aunque el episodio debería terminar.
        health_idx = max(0, int(spider_health) - 1)
        health_idx = min(health_idx, self.health_range - 1)

        # Ácido: Índice 0 a MAX_ACID.
        acid_idx = int(ant_acid)
        acid_idx = max(0, min(acid_idx, self.acid_range - 1))

        # Cooldown: 1 si está activo (>0), 0 si está listo.
        cooldown_idx = 1 if cooldown > 0 else 0

        # 3. Combinar en un único ID de estado (Mapeo a 1D / Fórmula de base mixta)

        state_id = dist_idx
        state_id = state_id * self.num_angle_bins + angle_idx
        state_id = state_id * self.health_range + health_idx
        state_id = state_id * self.acid_range + acid_idx
        state_id = state_id * self.cooldown_states + cooldown_idx

        return int(state_id)

# Función auxiliar utilizada en config.py (BASELINE/adapter)


def apply_adapter(env, **kwargs):
    return TacticalWrapper(env)
