# Requisitos de la Simulación: AntGuard-v1 (Modelo 2.5)

Este documento detalla las especificaciones técnicas para la implementación del entorno de Gymnasium AntGuard-v1, basado en el "Modelo 2.5: El Defensor Táctico".

## 1. Resumen del Entorno

* **Tipo**: Defensa de punto con gestión de recursos.
* **Agente**: Una hormiga soldado estática que defiende la entrada a las galerías inferiores del nido.
* **Enemigo**: Una araña depredadora que ha penetrado las defensas exteriores y avanza en zigzag.
* **Objetivo de RL**: Aprender una política de disparo eficiente que maximice el daño mientras conserva los recursos contra un objetivo con movimiento errático.
* **Escenario**: Un conducto cónico que se estrecha, simulando la entrada a las galerías inferiores de un nido.

## 2. Diseño y Apariencia

### 2.1. Escenario Cónico

El entorno de juego simula visualmente un túnel que se estrecha hacia el fondo, donde se encuentra la hormiga.

### 2.2. Hormiga Guardiana

**Apariencia**: Notablemente más grande que las hormigas de otras simulaciones, con una cabeza desproporcionadamente grande para enfatizar su rol de soldado.

### 2.3. Araña

**Apariencia**: De un tamaño significativamente mayor que la hormiga guardiana para representar una amenaza creíble.

## 3. Parámetros Configurables y Lógica de Tiempo

**Lógica de Tiempo**: Toda la dinámica se basa en fotogramas (frames).

* `SPIDER_HEALTH`: 3
* `ANT_ACID_TANK`: 5
* `SPIT_COOLDOWN_FRAMES`: 90
* `ROTATION_SPEED`, `SPIDER_SPEED`, `PROJECTILE_SPEED`

## 4. Entidades de la Simulación

### 4.1. Hormiga Guardiana (Agente)

* **Posición**: Fija en la parte inferior central del cono.
* **Estado** Interno: angle, acid_remaining, cooldown_timer_frames.
* **Acciones**: WAIT, ROTATE_LEFT, ROTATE_RIGHT, SPIT_ACID.

### 4.2. Araña (Enemigo)

Comportamiento:

* Aparece en la parte superior (la más ancha) del cono.
* **Movimiento en Zigzag**: La araña avanza hacia la hormiga, pero su trayectoria tiene una componente lateral que oscila, haciendo que se desplace de un lado a otro del cono.

### 4.3. Proyectil de Ácido

Comportamiento: 

* Se mueve en línea recta. Si colisiona con la Araña: `spider.health -= 1`. Se calcula si hay colisión desde el momento de lanzarse (haciendo un cálculo inmediato, para no dar recompensas en diferido).

## 5. Lógica del Entorno (Gymnasium)

### 5.1. Observation Space

```python
spaces.Dict({
    "distance": spaces.Box(low=np.array([0, -np.pi]), high=np.array([max_dist, np.pi]), dtype=np.float32),
    "vitals": spaces.Box(low=np.array([0, 0, 0]), high=np.array([SPIDER_HEALTH, ANT_ACID_TANK, SPIT_COOLDOWN_FRAMES]), dtype=np.float32)
})
```

### 5.2. Función step(action)

* **Actualizar Temporizadores**: `cooldown_timer_frames = max(0, cooldown_timer_frames - 1)`.
* **Ejecutar Acción**: Si la acción es `SPIT_ACID`, se calcula el resultado (hit/miss) instantáneamente.
* **Calcular Recompensa** (`reward`): Se asigna inmediatamente en función del resultado.
    * `-1` por fotograma.
    * `-5` por fallar un disparo.
    * `+30` por un impacto.
    * `+100` por el golpe final.
    * `-100` si la araña llega a la hormiga.
* **Actualizar Entidades**: Mover araña y proyectiles.
* **Determinar Fin de Episodio** (`terminated`): `True` si la vida de la araña llega a 0 o si la araña alcanza a la hormiga.

## 6. Efectos Visuales y de Jugabilidad

### 6.1. Animación de Ataque (Hormiga)

Al ejecutar la acción `SPIT_ACID`, la hormiga realiza una animación sutil (ej. una contracción) para indicar el disparo.

### 6.2. Efecto del Proyectil

El "escupitajo" es un proyectil visual que viaja en línea recta.

Se acompaña de un sistema de partículas que simula un "chorro" de color blanco o verde pálido. [Imagen de un chorro de ácido verde de videojuego]

### 6.3. Efecto de Impacto (Araña)

Cuando un proyectil colisiona con la araña:

* **Visual**: La araña parpadea en rojo o blanco.
* **Movimiento**: La araña se tambalea o es empujada ligeramente hacia atrás.

### 6.4. Animación de Muerte (Araña)

Cuando la vida de la araña llega a 0, ejecuta una animación de muerte (ej. se voltea) antes de desaparecer.

### 6.5. Animación de Derrota (Hormiga)

Si la araña alcanza a la hormiga, esta desaparece. La araña continúa hasta la entrada del nido y realiza una animación de "entrada" para señalizar el fin del episodio.

## 7. Lógica del Wrapper (TacticalWrapper)

**Propósito**: Actuar como un "traductor" entre el entorno complejo y el agente simple (QLearning). Convierte el Dict de observación con múltiples variables en un único número entero que puede ser usado como índice en una Q-Table.

Proceso:

1. **Recepción**: El wrapper intercepta el diccionario de observación del entorno.
2. **Discretización**: Convierte las variables continuas (distancia, ángulo) en un número de "cajones" o bins predefinidos (ej. 4 para distancia, 8 para ángulo).
3. **Normalización**: Se asegura de que las variables ya discretas (vida, ácido, recarga) se traten como índices numéricos.
4. **Mapeo a 1D**: Combina todos estos índices en un único ID de estado usando una fórmula de base mixta. Esto garantiza que cada posible combinación de (distancia, ángulo, vida, ácido, recarga) tenga un identificador numérico único.
    ```python
    # Ejemplo conceptual de la fórmula de mapeo:
    state_id = (((idx_dist * num_angles + idx_ang) * max_health + idx_health) * max_acid + idx_acid) * num_cd + idx_cd
    ```
5. **Salida**: Devuelve el state_id final como la nueva observación. El agente Q-Learning solo ve este número, ignorando por completo la complejidad original del problema.