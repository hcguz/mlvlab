import arcade

DESCRIPTION = "AntGuard-v1 (Escupidora Ácida): Defensa táctica y gestión de recursos. Aprende a optimizar disparos contra un enemigo errático usando Feature Engineering."

# Mapeo de teclas de Arcade a acciones del entorno (Action Space)
# 0: Wait, 1: Rotate Left (CCW), 2: Rotate Right (CW), 3: Spit Acid
KEY_MAP = {
    # Rotación
    arcade.key.LEFT: 1,
    arcade.key.A: 1,
    arcade.key.RIGHT: 2,
    arcade.key.D: 2,

    # Disparo
    arcade.key.SPACE: 3,
    arcade.key.UP: 3,
    arcade.key.W: 3,

    # Esperar (Opcional, pero mapeado)
    arcade.key.DOWN: 0,
    arcade.key.S: 0,
}

# Configuración del agente de referencia para 'train'
# Este entorno REQUIERE el uso del adaptador para ser resuelto con Q-Learning.
BASELINE = {
    "agent": "q_learning",
    "config": {
        # Con 1152 estados, necesitamos suficientes episodios para una buena exploración.
        "episodes": 1000,
        "alpha": 0.1,
        "gamma": 0.95,
        "epsilon_decay": 0.995,  # Decaimiento relativamente lento
        "min_epsilon": 0.05,
    }
}

# Unidad pedagógica a la que pertenece este entorno
UNIT = "ants"
ALGORITHM = "ql"
