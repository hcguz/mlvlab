import numpy as np

# Importación condicional de Arcade para asegurar compatibilidad en entornos sin gráficos.
try:
    import arcade
    DEFAULT_COLOR_ACID = arcade.color.LIME_GREEN
    ARCADE_AVAILABLE = True
except ImportError:
    # Fallback si arcade no está instalado (ej. servidor de entrenamiento)
    arcade = None
    # Color RGB fallback (Verde Lima)
    DEFAULT_COLOR_ACID = (50, 205, 50)
    ARCADE_AVAILABLE = False


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

    # --- NUEVO: Velocidad del proyectil (Visual, en unidades de mundo/paso) ---
    # Requisito 6.2. Calculado para cruzar la altura (100) en aprox 0.5s (15 frames). 100/15 ≈ 6.7
    VISUAL_PROJECTILE_SPEED = 7.0

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
    # Actualizado según Requirements.md (5.2)
    REWARD_MISS = -5
    # Actualizado según Requirements.md (5.2).
    REWARD_STEP = -1

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
    COLOR_ACID = DEFAULT_COLOR_ACID

    # --- Parámetros del Wrapper (Requisitos 7) ---
    WRAPPER_NUM_DIST_BINS = 4
    WRAPPER_NUM_ANGLE_BINS = 8

    @property
    def MAX_DIST(self):
        return np.sqrt(self.WORLD_HEIGHT**2 + (self.WORLD_WIDTH_TOP/2)**2)


# Instancia global de las constantes
C = AntGuardConstants()
