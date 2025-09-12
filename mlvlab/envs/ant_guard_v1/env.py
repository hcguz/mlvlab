import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Dict, Any

try:
    from .constants import C
    from .game import AntGuardGame
except ImportError:
    from constants import C
    from game import AntGuardGame


class AntGuardEnv(gym.Env):
    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_fps": C.RENDER_FPS
    }

    def __init__(self, render_mode: Optional[str] = None, **kwargs):
        self.render_mode = render_mode
        self.game = AntGuardGame(seed=kwargs.get('seed'))
        self.renderer = None

        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Dict({
            "distance": spaces.Box(
                low=np.array([0, -np.pi], dtype=np.float32),
                high=np.array([C.MAX_DIST, np.pi], dtype=np.float32),
                dtype=np.float32
            ),
            "vitals": spaces.Box(
                low=np.array([0, 0, 0], dtype=np.float32),
                high=np.array([C.SPIDER_HEALTH_MAX, C.ANT_ACID_TANK_MAX,
                              C.SPIT_COOLDOWN_FRAMES_MAX], dtype=np.float32),
                dtype=np.float32
            )
        })

    def _get_obs(self):
        return self.game._calculate_observation()

    def _get_info(self):
        return self.game.info

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        if seed is not None:
            self.game = AntGuardGame(seed=seed)

        self.game.reset()

        if self.renderer:
            self.renderer.reset()

        return self._get_obs(), self._get_info()

    def step(self, action):
        reward = self.game.update(action)
        terminated = self.game.game_over
        truncated = False

        observation = self._get_obs()
        info = self._get_info()

        if self.render_mode == "human":
            self.render()

        return observation, reward, terminated, truncated, info

    def render(self):
        if self.render_mode not in ["human", "rgb_array"]:
            return

        if self.renderer is None:
            try:
                from .renderer import AntGuardRenderer
                self.renderer = AntGuardRenderer(self.render_mode)
                # --- CORRECCIÓN DEL COLOR INICIAL ---
                # Se llama a reset() justo después de crear el renderer para asegurar
                # que el color aleatorio y otros estados visuales se inicialicen
                # antes del primer fotograma.
                self.renderer.reset()
            except ImportError as e:
                raise ImportError(
                    f"Could not import AntGuardRenderer. Please ensure Arcade is installed. Error: {e}")

        return self.renderer.update(self.game.get_state())

    def close(self):
        if self.renderer and self.renderer.window:
            self.renderer.window.close()
            self.renderer = None
