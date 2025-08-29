# AntMaze-v1 (Dungeons & Pheromones): Usage Guide

[![en](https://img.shields.io/badge/Lang-EN-red.svg)](./README.md)
[![es](https://img.shields.io/badge/Lang-ES-lightgrey.svg)](./README_es.md)

This file documents the `mlv/AntMaze-v1` environment, also known as **Dungeons & Pheromones**.

<img src="../../../docs/ant_maze_v1/mode_view_en.jpg" alt="view mode" width="100%">

## Description

In `AntMaze`, the student takes control of the learning process. An ant must navigate through a procedurally generated dungeon (maze) to find the exit. The goal is not just to solve the maze, but to understand how manipulating the fundamental hyperparameters of Reinforcement Learning (Alpha, Gamma, Epsilon) affects the agent's behavior and learning speed in real-time.

This simulation is designed to provide an interactive understanding of the exploration vs. exploitation dilemma and the impact of learning rate and discount factor.

---

## Thematic Interpretation

The hyperparameters are themed to match the dungeon scenario:

*   **Alpha (Learning Rate) → Pheromone Intensity:** How strongly the ant reinforces a path after taking it. A high value means rapid adaptation to new information; a low value means gradual learning.
*   **Gamma (Discount Factor) → Future Vision:** How much the ant values future rewards (the exit) compared to immediate ones. A high value encourages long-term planning, crucial in mazes.
*   **Epsilon (Exploration Rate) → Bravery (Exploration):** The probability that the ant ignores its knowledge (pheromones) and tries a new random path.

---

## Technical Sheet

### Environment Configuration

The environment can be customized when creating it:

*   `grid_size`: The size of the square dungeon (e.g., 15 for 15x15). Default is 15.
*   If `grid_size >= 10`, a complex maze is generated using Recursive Backtracking and BFS to ensure a challenging but always valid path.
*   If `grid_size < 10`, a simpler scenario is generated with random walls.

### Observation Space

The observation space defines what the agent "sees" at each step.
```
Box(0, GRID_SIZE-1, (2,), int32)
```
* **Meaning:** The observation is a vector with 2 integers, representing the ant's position `[x, y]` in the grid.
* **Limits:** Each coordinate ranges from 0 to GRID_SIZE-1, corresponding to a configurable grid size.

### Action Space

The action space defines what movements the agent can perform.
```
Discrete(4)
```
* **Meaning:** The agent can choose one of 4 discrete actions, represented by an integer:
    * `0`: Move **Up** (decreases the `y` coordinate)
    * `1`: Move **Down** (increases the `y` coordinate)
    * `2`: Move **Left** (decreases the `x` coordinate)
    * `3`: Move **Right** (increases the `x` coordinate)

---

## Environment Dynamics

### Rewards (Rewards)

The agent receives a signal (reward) after each action to guide its learning:
* **`+100`**: For reaching the dungeon exit.
* **`-10`**: For hitting a wall.
* **`-1`**: For each step taken. This incentivizes the agent to find the shortest path.

### Episode End (Termination & Truncation)

An "episode" (an attempt to find the exit) ends under the following conditions:
* **`terminated = True`**: The agent reaches the exit. The episode ends successfully.
* **`truncated = True`**: The maximum step limit is reached. This prevents the agent from wandering indefinitely.

**Important note:** If the ant hits a wall, it receives the penalty but **the episode does not end**. The ant remains in its current cell.

---

## Additional Information (`info`)

Both `reset()` and `step()` return an **`info`** dictionary, useful for debugging but **not recommended for direct use in training**.

---

### In `reset()`
| Key                 | Description                                        |
|---------------------|----------------------------------------------------|
| `grid_size`         | Size of the maze grid.                            |

---

### In `step()`
| Key                 | Description |
|---------------------|-------------|
| `grid_size`         | Size of the maze grid. |
| `collided`          | `True` if the ant collides against a wall. |
| `terminated`        | `True` if the episode ends because the ant reached the exit. |
| `play_sound`        | Dictionary with sound information:<br>• `{'filename': 'success.wav', 'volume': 10}` → when reaching the exit.<br>• `{'filename': 'bump.wav', 'volume': 7}` → when colliding with a wall. |

---

### Reset Behavior

When calling `reset()` without `seed`, the current dungeon is preserved and the ant returns to the start. A new dungeon is only generated if a `seed` is provided.

---

## Pheromone Visualization (Debug Mode)

When activating `debug` mode (Show Pheromones) in the interactive view, the learned Q-Table is visualized as a "pheromone trail". The color varies from pale pink (low value) to intense pink (high value), indicating the ant's preferred path.

---

## Recommended Training Strategy

### Algorithm: Q-Learning (tabular)

The combination of a **discrete state space** and a **discrete action space (4 actions)** makes this environment a perfect candidate for tabular algorithms like **Q-Learning**.

This method learns by creating a "lookup table" (the Q-Table) that stores the expected value for each action at each maze position, allowing the agent to determine the optimal policy.

---

## Shell Usage Examples

```bash
# Start MLVisual terminal
uv run mlv shell

# Play interactively in the environment
play AntMaze-v1

# Train an agent for a specific seed (e.g., 42)
train AntMaze-v1 --seed 42

# Train with a random seed
train AntMaze-v1

# Evaluate the last training in window mode
eval AntMaze-v1

# Evaluate a training from a specific seed
eval AntMaze-v1 --seed 42

# Evaluate a training with 100 episodes
eval AntMaze-v1 --eps 100

# Launch an interactive view to manipulate the environment using controls
view AntMaze-v1

# View this technical sheet from the terminal
docs AntMaze-v1
```

---

## Interaction (View Mode) - Recommended

The main method to interact with this environment is through `view` mode, which provides real-time controls for hyperparameters.

```bash
# Start MLVisual shell
uv run mlv shell

# Launch interactive view
view AntMaze-v1
```

In view mode:

1. Start the simulation.
2. Adjust the Alpha, Gamma, and Epsilon Decay sliders in real-time.
3. Activate "Debug Mode" to visualize the pheromone trail and observe how changes affect learning.

## Script and Notebook Compatibility

You can use **mlvlab** both in standalone scripts and interactive environments (Jupyter, Google Colab, etc.).  

---

### 1. Usage with Python Scripts

Create a dedicated virtual environment and install `mlvlab`:

```bash
# (Optional) Create a dedicated virtual environment
uv venv

# Install mlvlab within that virtual environment
uv pip install mlvlab

# Run your script within the virtual environment
uv run python my_script.py
```

### 2. Usage with Jupyter Notebooks

Simply select your virtual environment as kernel, or launch Jupyter with:

```bash
uv run jupyter notebook
```

### 3. Usage with Google Colab

Install `mlvlab` directly in the Colab session:

```bash
!pip install mlvlab
```

### Quick examples for notebooks

```python
# Create the environment and run a random episode
import gymnasium as gym
import mlvlab  # registers the "mlv/..." environments

try:
    env = gym.make("mlv/AntMaze-v1", render_mode="human", grid_size=15)
    obs, info = env.reset(seed=42)
    terminated = truncated = False

    while not (terminated or truncated):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
    env.close()
except gym.error.NameNotFound:
    print("Error: mlv/AntMaze-v1 not registered.")
```

```python
# Tabular training with Q-Learning agent from the package
from mlvlab.agents.q_learning import QLearningAgent
import gymnasium as gym
import mlvlab  # registers the "mlv/..." environments

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
    print("Error: mlv/AntMaze-v1 not registered.")
```

```python
# Tabular training (Q-Table) with simplified algorithm
import numpy as np
import gymnasium as gym
import mlvlab  # registers the "mlv/..." environments

try:
    env = gym.make("mlv/AntMaze-v1", grid_size=15)
    GRID = int(env.unwrapped.GRID_SIZE)
    N_S, N_A = GRID * GRID, 4  # We use only the 4 movement actions for learning
    Q = np.zeros((N_S, N_A), dtype=np.float32)

    def obs_to_state(obs):
        x, y = int(obs[0]), int(obs[1])
        return y * GRID + x

    # Hyperparameters
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

            # Q-Learning update rule
            Q[s, a] = (1 - alpha) * Q[s, a] + alpha * (r + gamma * Q[s2].max())
            s = s2
            done = term or trunc

        # Epsilon decay
        eps = max(0.01, eps * eps_decay)

    env.close()
except gym.error.NameNotFound:
    print("Error: mlv/AntMaze-v1 not registered.")
```

**Suggestion**: Save and load the Q-Table/weights to reuse them between sessions. You can also train from the shell and evaluate in notebook, or vice versa.

---

## Environment Actions (Optional)

The `AntMaze` environment includes special action functions that can be called directly for testing and experimentation purposes:

### `action_shift()`

This function allows you to change the maze while preserving the learned Q-Table, enabling continuous learning across different environments:

```python
# In scripts or notebooks
obs, info = env.action_shift()
```

**What it does:**
1. **Blocks Q-Values**: Temporarily locks the Q-Table to prevent updates during the transition
2. **Changes Map**: Generates a new maze layout while keeping the same grid size
3. **Unlocks Q-Values**: Re-enables learning, allowing the agent to continue improving with the new maze

**Use Cases:**
- **Testing Adaptation**: See how well your trained agent adapts to new maze layouts
- **Continuous Learning**: Maintain learning progress while exploring different environments
- **Research**: Study transfer learning and generalization capabilities

### `action_toggle_pheromones()`

This function toggles between different pheromone visualization modes for debugging and analysis:

```python
# In scripts or notebooks
obs, info = env.action_toggle_pheromones()
```

**What it does:**
1. **Toggles Visualization**: Switches between "discovered" and "global" pheromone display modes
2. **Auto-Debug Mode**: Automatically activates debug mode when global pheromone visualization is enabled
3. **UI Synchronization**: Updates the UI state to reflect the current visualization mode

**Visualization Modes:**
- **Discovered Mode**: Shows only the pheromone trail that the agent has explored
- **Global Mode**: Shows the complete pheromone map across the entire maze (requires debug mode)

**Use Cases:**
- **Debug Analysis**: Examine the complete learning state across the entire maze
- **Performance Comparison**: Compare discovered vs. global pheromone patterns
- **Research**: Study exploration patterns and learning coverage

**Note:** These actions are automatically mapped in the interactive views, so you don't need to implement them manually in your training loops.
