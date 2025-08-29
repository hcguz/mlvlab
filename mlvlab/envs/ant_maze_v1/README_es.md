# AntMaze-v1 (Feromonas y Mazmorras): Guía de Uso

[![en](https://img.shields.io/badge/Lang-EN-lightgrey.svg)](./README.md)
[![es](https://img.shields.io/badge/Lang-ES-red.svg)](./README_es.md)

Este archivo documenta el entorno `mlv/AntMaze-v1`, también conocido como **Dungeons & Pheromones**.

<img src="../../../docs/ant_maze_v1/mode_view_es.jpg" alt="view mode" width="100%">

## Descripción

En `AntMaze`, el estudiante toma el control del proceso de aprendizaje. Una hormiga debe navegar por una mazmorra (laberinto) generada proceduralmente para encontrar la salida. El objetivo no es solo resolver el laberinto, sino comprender cómo la manipulación de los hiperparámetros fundamentales del Reinforcement Learning (Alpha, Gamma, Epsilon) afecta el comportamiento del agente y la velocidad de aprendizaje en tiempo real.

Esta simulación está diseñada para proporcionar una comprensión interactiva del dilema exploración vs. explotación y el impacto del ratio de aprendizaje y el factor de descuento.

---

## Interpretación Temática

Los hiperparámetros están tematizados para coincidir con el escenario de la mazmorra:

*   **Alpha (Learning Rate) → Intensidad de las Feromonas:** Qué tan fuertemente la hormiga refuerza un camino después de tomarlo. Un valor alto significa adaptación rápida a nueva información; un valor bajo significa aprendizaje gradual.
*   **Gamma (Discount Factor) → Visión de Futuro:** Cuánto valora la hormiga las recompensas futuras (la salida) en comparación con las inmediatas. Un valor alto fomenta la planificación a largo plazo, crucial en laberintos.
*   **Epsilon (Exploration Rate) → Valentía (Exploración):** La probabilidad de que la hormiga ignore su conocimiento (feromonas) e intente un camino nuevo y aleatorio.

---

## Ficha Técnica

### Configuración del Entorno

El entorno se puede personalizar al crearlo:

*   `grid_size`: El tamaño de la mazmorra cuadrada (ej. 15 para 15x15). Por defecto es 15.
*   Si `grid_size >= 10`, se genera un laberinto complejo usando Recursive Backtracking y BFS para asegurar un camino desafiante pero siempre válido.
*   Si `grid_size < 10`, se genera un escenario más simple con muros aleatorios.

### Observation Space

El espacio de observación define lo que el agente "ve" en cada paso.
```
Box(0, GRID_SIZE-1, (2,), int32)
```
* **Significado:** La observación es un vector con 2 números enteros, que representan la posición `[x, y]` de la hormiga en la rejilla.
* **Límites:** Cada coordenada va de 0 a GRID_SIZE-1, correspondiendo a una rejilla de tamaño configurable.

### Action Space

El espacio de acciones define qué movimientos puede realizar el agente.
```
Discrete(4)
```
* **Significado:** El agente puede elegir una de 4 acciones discretas, representadas por un número entero:
    * `0`: Moverse **Arriba** (disminuye la coordenada `y`)
    * `1`: Moverse **Abajo** (aumenta la coordenada `y`)
    * `2`: Moverse a la **Izquierda** (disminuye la coordenada `x`)
    * `3`: Moverse a la **Derecha** (aumenta la coordenada `x`)

---

## Dinámica del Entorno

### Recompensas (Rewards)

El agente recibe una señal (recompensa) después de cada acción para guiar su aprendizaje:
* **`+100`**: Por alcanzar la salida de la mazmorra.
* **`-10`**: Por chocar contra un muro.
* **`-1`**: Por cada paso dado. Esto incentiva al agente a encontrar la ruta más corta.

### Fin del Episodio (Termination & Truncation)

Un "episodio" (un intento de encontrar la salida) termina bajo las siguientes condiciones:
* **`terminated = True`**: El agente alcanza la salida. El episodio termina con éxito.
* **`truncated = True`**: Se alcanza el límite máximo de pasos. Esto evita que el agente vague indefinidamente.

**Nota importante:** Si la hormiga choca contra un muro, recibe la penalización pero **el episodio no termina**. La hormiga permanece en su celda actual.

---

## Información Adicional (`info`)

Tanto `reset()` como `step()` devuelven un diccionario **`info`**, útil para depuración pero **no recomendado para usar directamente en el entrenamiento**.

---

### En `reset()`
| Clave              | Descripción                                        |
|---------------------|----------------------------------------------------|
| `grid_size`        | Tamaño de la cuadrícula del laberinto.            |

---

### En `step()`
| Clave              | Descripción |
|---------------------|-------------|
| `grid_size`        | Tamaño de la cuadrícula del laberinto. |
| `collided`         | `True` si la hormiga colisiona contra un muro. |
| `terminated`       | `True` si el episodio termina porque la hormiga alcanzó la salida. |
| `play_sound`       | Diccionario con información de sonido:<br>• `{'filename': 'success.wav', 'volume': 10}` → al alcanzar la salida.<br>• `{'filename': 'bump.wav', 'volume': 7}` → al colisionar con un muro. |

---

### Comportamiento del Reset

Al llamar a `reset()` sin `seed`, la mazmorra actual se conserva y la hormiga vuelve al inicio. Solo se genera una nueva mazmorra si se proporciona una `seed`.

---

## Visualización de Feromonas (Modo Debug)

Al activar el modo `debug` (Mostrar Feromonas) en la vista interactiva, la Q-Table aprendida se visualiza como un "rastro de feromonas". El color varía desde rosa pálido (bajo valor) hasta rosa intenso (alto valor), indicando el camino preferido por la hormiga.

---

## Estrategia de Entrenamiento Recomendada

### Algoritmo: Q-Learning (tabular)

La combinación de un **espacio de estados discreto** y un **espacio de acciones discreto (4 acciones)** hace que este entorno sea un candidato perfecto para algoritmos tabulares como **Q-Learning**.

Este método aprende creando una "tabla de consulta" (la Q-Table) que almacena el valor esperado para cada acción en cada posición del laberinto, permitiendo al agente determinar la política óptima.

---

## Ejemplos de Uso con el Shell

```bash
# Inicia la terminal de MLVisual
uv run mlv shell

# Jugar interactivamente en el entorno
play AntMaze-v1

# Entrenar un agente para una semilla específica (p. ej. 42)
train AntMaze-v1 --seed 42

# Entrenar con una semilla aleatoria
train AntMaze-v1

# Evaluar el último entrenamiento en modo ventana
eval AntMaze-v1

# Evaluar un entrenamiento de una semilla específica
eval AntMaze-v1 --seed 42

# Evaluar un entrenamiento de 100 episodios
eval AntMaze-v1 --eps 100

# Lanza una vista interactiva para manipular el entorno usando controles
view AntMaze-v1

# Ver esta ficha técnica desde la terminal
docs AntMaze-v1
```

---

## Interacción (Modo View) - Recomendado

El método principal para interactuar con este entorno es a través del modo `view`, que proporciona controles en tiempo real para los hiperparámetros.

```bash
# Inicia la terminal de MLVisual
uv run mlv shell

# Lanzar la vista interactiva
view AntMaze-v1
```

En el modo view:

1. Inicia la simulación.
2. Ajusta los sliders de Alpha, Gamma y Epsilon Decay en tiempo real.
3. Activa el "Modo Debug" para visualizar el rastro de feromonas y observa cómo los cambios afectan el aprendizaje.

## Compatibilidad con Scripts y Notebooks

Puedes usar **mlvlab** tanto en scripts independientes como en entornos interactivos (Jupyter, Google Colab, etc.).  

---

### 1. Uso con Scripts de Python

Crea un entorno virtual dedicado e instala `mlvlab`:

```bash
# (Opcional) Crea un entorno virtual dedicado
uv venv

# Instala mlvlab dentro de ese entorno virtual
uv pip install mlvlab

# Ejecuta tu script dentro del entorno virtual
uv run python mi_script.py
```

### 2. Uso con Jupyter Notebooks

Simplemente selecciona tu entorno virtual como kernel, o lanza Jupyter con:

```bash
uv run jupyter notebook
```

### 3. Uso con Google Colab

Instala `mlvlab` directamente en la sesión de Colab:

```bash
!pip install mlvlab
```

###  Ejemplos rápidos para cuadernos

```python
# Crear el entorno y ejecutar un episodio aleatorio
import gymnasium as gym
import mlvlab  # registra los entornos "mlv/..."

try:
    env = gym.make("mlv/AntMaze-v1", render_mode="human", grid_size=15)
    obs, info = env.reset(seed=42)
    terminated = truncated = False

    while not (terminated or truncated):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
    env.close()
except gym.error.NameNotFound:
    print("Error: mlv/AntMaze-v1 no registrado.")
```

```python
# Entrenamiento tabular con agente Q-Learning del paquete
from mlvlab.agents.q_learning import QLearningAgent
import gymnasium as gym
import mlvlab  # registra los entornos "mlv/..."

try:
    env = gym.make("mlv/AntMaze-v1", grid_size=15)
    obs, info = env.reset(seed=42)

    agent = QLearningAgent(
        observation_space=env.observation_space,
        action_space=env.action_space,
        learning_rate=0.1,
        discount_factor=0.99,
        epsilon=1.0,
        epsilon_decay=0.995,
        min_epsilon=0.01
    )

    n_steps = 100
    for _ in range(n_steps):
        action = agent.act(obs)
        next_obs, reward, terminated, truncated, info = env.step(action)
        agent.learn(obs, action, reward, next_obs, terminated)
        obs = next_obs
        if terminated or truncated:
            obs, info = env.reset()
    env.close()
except gym.error.NameNotFound:
    print("Error: mlv/AntMaze-v1 no registrado.")
```

```python
# Entrenamiento tabular (Q-Table) con algoritmo simplificado
import numpy as np
import gymnasium as gym
import mlvlab  # registra los entornos "mlv/..."

try:
    env = gym.make("mlv/AntMaze-v1", grid_size=15)
    GRID = int(env.unwrapped.GRID_SIZE)
    N_S, N_A = GRID * GRID, 4  # Usamos solo las 4 acciones de movimiento para aprender
    Q = np.zeros((N_S, N_A), dtype=np.float32)

    def obs_to_state(obs):
        x, y = int(obs[0]), int(obs[1])
        return y * GRID + x

    # Hiperparámetros
    alpha, gamma, eps = 0.1, 0.95, 1.0
    eps_decay = 0.999

    for ep in range(500):
        obs, info = env.reset()
        s = obs_to_state(obs)
        done = False
        while not done:
            if np.random.rand() < eps:
                a = np.random.randint(N_A)
            else:
                a = int(Q[s].argmax())

            obs2, r, term, trunc, info = env.step(a)
            s2 = obs_to_state(obs2)

            # Regla de actualización Q-Learning
            Q[s, a] = (1 - alpha) * Q[s, a] + alpha * (r + gamma * Q[s2].max())
            s = s2
            done = term or trunc

        # Decaimiento de Epsilon
        eps = max(0.01, eps * eps_decay)

    env.close()
except gym.error.NameNotFound:
    print("Error: mlv/AntMaze-v1 no registrado.")
```

**Sugerencia**: Guarda y carga la Q-Table/pesos para reutilizarlos entre sesiones. También puedes entrenar desde el shell y evaluar en notebook, o al revés.

---

## Acciones del Entorno (Opcional)

El entorno `AntMaze` incluye funciones de acción especiales que se pueden llamar directamente para pruebas y experimentación:

### `action_shift()`

Esta función te permite cambiar el laberinto mientras preservas la Q-Table aprendida, permitiendo el aprendizaje continuo en diferentes entornos:

```python
# En scripts o notebooks
obs, info = env.action_shift()
```

**Qué hace:**
1. **Bloquea Q-Values**: Bloquea temporalmente la Q-Table para evitar actualizaciones durante la transición
2. **Cambia el Mapa**: Genera un nuevo diseño de laberinto manteniendo el mismo tamaño de cuadrícula
3. **Desbloquea Q-Values**: Re-activa el aprendizaje, permitiendo que el agente continúe mejorando con el nuevo laberinto

**Casos de Uso:**
- **Pruebas de Adaptación**: Ver qué tan bien se adapta tu agente entrenado a nuevos diseños de laberinto
- **Aprendizaje Continuo**: Mantener el progreso de aprendizaje mientras exploras diferentes entornos
- **Investigación**: Estudiar capacidades de transferencia de aprendizaje y generalización

### `action_toggle_pheromones()`

Esta función alterna entre diferentes modos de visualización de feromonas para depuración y análisis:

```python
# En scripts o notebooks
obs, info = env.action_toggle_pheromones()
```

**Qué hace:**
1. **Alterna Visualización**: Cambia entre modos de visualización de feromonas "descubiertas" y "global"
2. **Modo Debug Automático**: Activa automáticamente el modo debug cuando se habilita la visualización global de feromonas
3. **Sincronización UI**: Actualiza el estado de la UI para reflejar el modo de visualización actual

**Modos de Visualización:**
- **Modo Descubierto**: Muestra solo el rastro de feromonas que el agente ha explorado
- **Modo Global**: Muestra el mapa completo de feromonas en todo el laberinto (requiere modo debug)

**Casos de Uso:**
- **Análisis de Debug**: Examinar el estado completo de aprendizaje en todo el laberinto
- **Comparación de Rendimiento**: Comparar patrones de feromonas descubiertas vs. globales
- **Investigación**: Estudiar patrones de exploración y cobertura de aprendizaje

**Nota:** Estas acciones se mapean automáticamente en las vistas interactivas, por lo que no necesitas implementarlas manualmente en tus bucles de entrenamiento.
