# mlvlab/envs/ant_guard_v1/view.py
import gymnasium as gym
import numpy as np

# Imports de mlvlab para la vista interactiva
try:
    from mlvlab.agents.q_learning import QLearningAgent
    from mlvlab.core.logic import InteractiveLogic
    from mlvlab.core.trainer import Trainer
    from mlvlab.ui import AnalyticsView
    from mlvlab import ui
except ImportError:
    print("ADVERTENCIA: mlvlab no detectado. La vista interactiva requiere mlvlab.")
    # Definiciones dummy para que el archivo sea importable sin mlvlab
    QLearningAgent = None
    InteractiveLogic = object
    Trainer = None
    AnalyticsView = None
    ui = None

# Imports específicos del entorno
try:
    from .adapters import TacticalWrapper
    from .constants import C
except ImportError:
    # Fallback para ejecución directa
    from adapters import TacticalWrapper
    from constants import C


class AntGuardLogic(InteractiveLogic):
    """
    Lógica interactiva para el entorno AntGuard-v1.
    """

    def _obs_to_state(self, obs):
        """
        Convierte la observación del entorno (ya procesada por el wrapper) a un estado.
        Como el TacticalWrapper ya devuelve un entero, solo necesitamos asegurar el tipo.
        """
        return int(obs)

    def step(self, state):
        """
        Ejecuta un paso de la simulación: el agente actúa, el entorno responde y el agente aprende.
        """
        # 1. El agente decide la acción
        action = self.agent.act(state)

        # 2. El entorno ejecuta la acción
        next_obs, reward, terminated, truncated, info = self.env.step(action)
        next_state = self._obs_to_state(next_obs)
        done = bool(terminated or truncated)

        # 3. El agente aprende de la experiencia
        self.agent.learn(state, action, reward, next_state, done)

        self.total_reward += reward
        return next_state, reward, done, info


def main():
    """Función principal para lanzar la vista interactiva."""
    if AnalyticsView is None:
        print("ERROR: No se pueden cargar los componentes de la UI de mlvlab.")
        return

    # 1. Crear el entorno base
    env_name = "mlv/AntGuard-v1"
    try:
        env = gym.make(env_name, render_mode="rgb_array")
    except gym.error.NameNotFound:
        print(
            f"ERROR: Entorno '{env_name}' no encontrado. Asegúrate de que esté registrado.")
        return
    except Exception as e:
        print(f"Error al crear el entorno: {e}")
        return

    # 2. ENVOLVER EL ENTORNO. Este es el paso clave.
    # El TacticalWrapper convierte el Dict de observación en un solo entero,
    # haciendo que sea compatible con QLearningAgent.
    env = TacticalWrapper(env)

    # 3. Configurar el agente Q-Learning
    # Ahora, el espacio de observación del 'env' envuelto es Discrete.
    agent = QLearningAgent(
        observation_space=env.observation_space,
        action_space=env.action_space,
        learning_rate=0.1,      # Alpha (Tasa de aprendizaje)
        discount_factor=0.95,   # Gamma (Factor de descuento)
        epsilon=1.0,            # Epsilon inicial (Exploración)
        epsilon_decay=0.9995,   # Decaimiento lento para un espacio de estados grande
        min_epsilon=0.05
    )

    # 4. Crear el Trainer
    trainer = Trainer(env, agent, AntGuardLogic, 1)

    # 5. Configurar y lanzar la vista interactiva
    view = AnalyticsView(
        trainer=trainer,
        title="AntGuard-v1 (Escupidora Ácida)",
        left_panel=[
            ui.SimulationControls(
                includes=["speed", "turbo"],
                # No hay modo debug visual de Q-table
                buttons=["play", "reset", "sound"]
            ),
            # Panel para ajustar los hiperparámetros en tiempo real
            ui.AgentHyperparameters(
                params={
                    "learning_rate", "discount_factor", "epsilon_decay"
                },
            ),
            # Panel para guardar y cargar el agente entrenado
            ui.ModelPersistence(default_filename="ant_guard_qt.npz"),
        ],
        right_panel=[
            # Métricas clave de rendimiento
            ui.MetricsDashboard(
                metrics=["epsilon", "current_reward",
                         "episodes_completed", "steps_per_second", "seed"],
            ),
            # Gráfico de recompensas
            ui.RewardChart(history_size=100),
        ],
    )

    view.run()


if __name__ == "__main__":
    main()
