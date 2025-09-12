# AntGuard-v1 (Escupidora Ácida): Guía de Uso

[![en](https://img.shields.io/badge/Lang-EN-lightgrey.svg)](./README.md)
[![es](https://img.shields.io/badge/Lang-ES-red.svg)](./README_es.md)

Este archivo documenta el entorno `mlv/AntGuard-v1`, también conocido como **Escupidora Ácida**.

<img src="../../../docs/ant_guard_v1/mode_view_es.jpg" alt="view mode" width="100%">

## Descripción

En `AntGuard`, el estudiante se enfrenta a un desafío fundamental en Reinforcement Learning: cómo manejar un problema complejo con un agente simple. El agente es una hormiga soldado estática que defiende su nido de una araña que se acerca.

El objetivo es aprender a resolver un problema con un espacio de estados complejo mediante el **feature engineering**. El éxito del agente depende no solo de su percepción [distancia, ángulo], sino también de la **gestión de recursos limitados**: la vida de la araña, un tanque de ácido finito y un tiempo de recarga tras cada disparo. Esta simulación enseña cómo abstraer y discretizar un problema estratégico para que pueda ser resuelto por algoritmos simples como Q-Learning.

---

## Interpretación Temática

El éxito de la hormiga depende de su **eficiencia táctica**. No puede disparar a lo loco.


*  **Estado (Observación) → Conciencia Situacional**: La hormiga debe evaluar la amenaza (distancia, ángulo, vida_araña) en el contexto de sus propios recursos (ácido_restante, recarga_activa).
*  **Aprendizaje → Instinto de Supervivencia**: El agente aprende una política sofisticada. No solo "¿debo disparar?", sino "¿Es este el mejor momento para disparar? ¿Puedo permitirme fallar? ¿Es mejor esperar a tener un tiro más claro?".

---

## Ficha Técnica

### Observation Space (Original)

El espacio de observación del entorno combina valores continuos y discretos, haciéndolo incompatible con Q-Learning tabular directamente:

- Distancia a la araña (`float`)
- Ángulo relativo de la araña (`float`)
- Vida restante de la araña (`int`)
- Ácido restante de la hormiga (`int`)
- Temporizador de recarga activo (`bool/float`)
  
**Problema**: La combinación de valores continuos y el gran número de combinaciones de estados hacen que una Q-Table sea inviable sin una capa de abstracción.

### Action Space

El espacio de acciones define qué movimientos puede realizar el agente.

```
Discrete(4)
```
* **Significado:** El agente puede elegir una de 4 acciones discretas:
    * `0`: **Esperar**
    * `1`: **Rotar a la Izquierda**
    * `2`: **Rotar a la Derecha**
    * `3`: **Escupir Ácido Fórmico** (si no está en recarga y tiene ácido)

---

## Dinámica del Entorno

### Recompensas (Rewards)

La señal de recompensa está diseñada para fomentar un comportamiento táctico:

* **`+100`**: Por asestar el golpe final que derrota a la araña.
* **`+30`**: Por cada golpe que daña a la araña pero no la derrota.
* **`-100`**: Si la araña alcanza a la hormiga.
* **`-5`**: Por escupir ácido y fallar.
* **`-1`**: Por cada paso de tiempo (incentiva la rapidez).

### Fin del Episodio (Termination & Truncation)

Un episodio termina cuando:

* **`terminated = True`**: La vida de la araña llega a 0 (éxito) o la araña alcanza a la hormiga (fracaso).
* **`truncated = True`**: Se alcanza el límite máximo de pasos.

---

## TODO: Información Adicional (`info`)

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

### Algoritmo: Q-Learning + Wrapper de Discretización Complejo

La solución es un `gymnasium.Wrapper` que discretiza las variables continuas y mapea el estado completo a un único entero para la Q-Table.

1. **El Problema**: El QLearningAgent no puede manejar el vector de estado mixto.
2. **La Solución**: El DiscretizingWrapper intercepta el vector de estado.
3. **La Abstracción**: El wrapper convierte [distancia, ángulo] en índices discretos y luego combina estos con los valores ya discretos *(vida_araña, ácido_restante, recarga_activa)* para producir un único ID de estado.
4. **El Resultado**: El QLearningAgent puede aprender una política compleja sin cambiar su lógica interna. El número total de estados, aunque grande, es manejable: *4 (dist) * 8 (ang) * 3 (vida) * 6 (ácido) * 2 (recarga) = 1152 estados*.

---

## Ejemplos de Uso

```bash
# Inicia la terminal de MLVisual
uv run mlv shell

# Jugar interactivamente en el entorno
play AntGuard-v1

# Entrenar un agente para una semilla específica (p. ej. 42)
train AntGuard-v1 --seed 42

# Entrenar con una semilla aleatoria
train AntGuard-v1

# Evaluar el último entrenamiento en modo ventana
eval AntGuard-v1

# Evaluar un entrenamiento de una semilla específica
eval AntGuard-v1 --seed 42

# Evaluar un entrenamiento de 100 episodios
eval AntGuard-v1 --eps 100

# Lanza una vista interactiva para manipular el entorno usando controles
view AntGuard-v1

# Ver esta ficha técnica desde la terminal
docs AntGuard-v1
```

---

En el modo *view*, podrás observar el comportamiento táctico del agente y visualizar en la UI la vida de la araña, el ácido restante y el estado de la recarga.

---

###  Ejemplos de Implementación

El código muestra cómo el wrapper maneja el nuevo espacio de estados:

```python
import gymnasium as gym
import numpy as np
import mlvlab  # registra los entornos "mlvlab/..."

class TacticalWrapper(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        
        # Parámetros de discretización
        self.num_dist_bins = 4
        self.num_angle_bins = 8
        
        # Límites de los nuevos estados discretos (obtenidos del entorno original)
        self.spider_max_health = 3  # Asumimos 3 HP
        self.ant_max_acid = 5       # Asumimos 5 disparos
        self.cooldown_states = 2    # Activo o no activo
        
        # El tamaño total del nuevo espacio de observación discreto
        total_states = (self.num_dist_bins *
                        self.num_angle_bins *
                        self.spider_max_health *
                        self.ant_max_acid *
                        self.cooldown_states)
        self.observation_space = gym.spaces.Discrete(total_states)
        
        self.max_dist = self.env.observation_space['distance'].high[0]

    def observation(self, obs):
        # obs es ahora un diccionario, ej: {'distance': [dist, angle], 'vitals': [health, acid, cd]}
        dist, angle = obs['distance']
        spider_health, ant_acid, cooldown = obs['vitals']
        
        # 1. Discretizar las variables continuas
        dist_bin_index = np.digitize(dist, bins=np.linspace(0, self.max_dist, self.num_dist_bins)) - 1
        angle_bin_index = np.digitize(angle, bins=np.linspace(-np.pi, np.pi, self.num_angle_bins)) - 1
        
        # Asegurar que los índices estén dentro de los límites
        dist_bin_index = max(0, min(dist_bin_index, self.num_dist_bins - 1))
        angle_bin_index = max(0, min(angle_bin_index, self.num_angle_bins - 1))
        
        # 2. Las variables discretas ya están listas (solo hay que asegurarse de que sean enteros)
        health_index = int(spider_health)
        acid_index = int(ant_acid)
        cooldown_index = 1 if cooldown > 0 else 0
        
        # 3. Combinar todos los índices en un único ID de estado
        # Esta fórmula es la clave del mapeo de un espacio multidimensional a 1D
        state_id = cooldown_index
        state_id = state_id * self.ant_max_acid + acid_index
        state_id = state_id * self.spider_max_health + health_index
        state_id = state_id * self.num_angle_bins + angle_bin_index
        state_id = state_id * self.num_dist_bins + dist_bin_index
        
        return int(state_id)

# --- Flujo de Entrenamiento ---
# (El resto del código de entrenamiento sería similar, usando el QLearningAgent
# con el 'env_traducido' que se crearía a partir de este wrapper)
```