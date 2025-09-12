import numpy as np
import arcade


class AntGuardConstants:
    # --- Parámetros de Simulación (Requisitos 3) ---
    SPIDER_HEALTH_MAX = 3
    ANT_ACID_TANK_MAX = 5
    SPIT_COOLDOWN_FRAMES_MAX = 90  # 3 segundos a 30 FPS
    MAX_EPISODE_STEPS = 1000

    # --- Parámetros de Movimiento ---
    # Ángulo en Radianes por paso (Aprox 4.5 grados)
    ROTATION_SPEED = 0.08
    # Unidades de mundo por paso
    SPIDER_SPEED = 0.6
    ZIGZAG_FREQUENCY = 0.05

    # --- Dimensiones del Mundo (Lógica Cónica) ---
    WORLD_HEIGHT = 100.0
    WORLD_WIDTH_TOP = 80.0
    WORLD_WIDTH_BOTTOM = 20.0
    # Hitbox de la araña
    SPIDER_RADIUS = 4.0

    # --- Recompensas (Requisitos 5.2) ---
    REWARD_KILL = 100
    REWARD_HIT = 30
    REWARD_LOSE = -100
    REWARD_MISS = 0
    # --- CAMBIO CLAVE: Aumentamos la penalización por paso ---
    # Esto crea una "urgencia" para que el agente actúe en lugar de
    # simplemente esperar y acumular una pequeña penalización.
    REWARD_STEP = -2

    # --- Configuración de Renderizado (Arcade) ---
    SCREEN_WIDTH = 600
    GAME_HEIGHT = 700
    UI_HEIGHT = 100
    WINDOW_HEIGHT = GAME_HEIGHT + UI_HEIGHT
    RENDER_FPS = 30

    # Colores
    COLOR_BG_OUTSIDE = (30, 20, 10)
    COLOR_BG_TUNNEL = (60, 40, 25)
    COLOR_WALL = (100, 70, 40)
    COLOR_ACID = arcade.color.LIME_GREEN

    # --- Parámetros del Wrapper (Requisitos 7) ---
    WRAPPER_NUM_DIST_BINS = 4
    WRAPPER_NUM_ANGLE_BINS = 8

    @property
    def MAX_DIST(self):
        return np.sqrt(self.WORLD_HEIGHT**2 + (self.WORLD_WIDTH_TOP/2)**2)


# Instancia global de las constantes
C = AntGuardConstants()
