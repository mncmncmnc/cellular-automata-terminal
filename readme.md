# life.py

Conway's Game of Life for the terminal, mostly adapted from a bootleg 1990s Turbo Pascal version a friend gave me

## Quick start

```
python3 life.py --pattern glider --speed 20      # glider, moving
python3 life.py --pattern gosper_gun             # gun that fires gliders
python3 life.py --pattern r_pentomino            # chaotic methuselah
python3 life.py --random 25 --theme rainbow      # 25% random, color by age
python3 life.py --list-patterns                  # see everything available
```

## In-app quick reference

| Key | Action |
|-----|--------|
| `enter` | Play / pause |
| `space` | Toggle cell under cursor |
| `p` | Open pattern picker (browse, pick, rotate with `[` / `]`, stamp) |
| `t` | Cycle theme (green -> yellow -> white -> rainbow) |
| `g` | Toggle grid lines |
| `+` / `-` | Speed up / down |
| `?` | Full help overlay |
| `q` | Quit |

## Running

```
python3 life.py [options]
```

## CLI flags

| Flag | Description |
|------|-------------|
| `--pattern NAME` | Start with a named pattern centered on the grid |
| `--random PCT` | Random-fill the grid at PCT% density (0-100) |
| `--speed N` | Initial speed in generations per second (1-60, default 10) |
| `--theme NAME` | Starting color theme: green, yellow, white, rainbow (default: green) |
| `--no-grid` | Start with grid dot markers off |
| `--bounded` | Use bounded edges instead of wrap-around |
| `--width N` | Grid width in cells (default: fits terminal) |
| `--height N` | Grid height in cells (default: fits terminal) |
| `--load FILE` | Load a previously saved state from a JSON file |
| `--list-patterns` | Print all available pattern names by category, then exit |

---

## Controls

### Navigation
*(cursor only moves while paused right now sorry)*

```
arrows  or  hjkl    Move cursor one cell
```

### Editing

```
space    Toggle cell under cursor alive / dead
r        Random fill -- each press cycles through 10%, 25%, 50% density
c        Clear all cells and reset the generation counter
p        Open the pattern picker (see below)
```

### Playback

```
enter      Play / pause simulation
n  or  .   Step forward one generation (paused only)
+  or  =   Speed up (max 60 gen/s)
-          Slow down (min 1 gen/s)
```

### Display

```
g    Toggle grid dot markers on / off
t    Cycle theme: green -> yellow -> white -> rainbow
```

In rainbow mode, each cell's color shifts based on how many generations it has
been alive. 

### Simulation behavior

```
b    Toggle wrap / bounded edges
```

- **wrap** (default): Cells leaving one edge reappear on
  the opposite side i.e. patterns can travel indefinitely.
- **bounded**: Patterns that reach the edge will interact with it (and usually die or reflect).

### Save / Load

```
s    Save current state to ~/.life/state-<timestamp>.json
l    Load the most recent save from ~/.life/
```

Saves store generation count, grid dimensions, wrap setting, and
cell coordinates. The `~/.life/` directory is created automatically on first save.
You can also load a file at launch with `--load <file>`.

### Other

```
?    In-app help overlay
q    Quit
```

---

## Pattern picker

Open with `p`. The simulation pauses automatically.

**Browsing:** `up` / `down` arrows (or `k` / `j`) navigate the list. Press `enter` to select.

**Placement:** After selecting a pattern, a ghost preview appears on the grid.

```
arrows  or  hjkl    Move the ghost
[                   Rotate 90° counter-clockwise
]                   Rotate 90° clockwise
enter               Stamp the pattern onto the grid
esc  or  q          Cancel without placing
```

---

## Pattern library

### Still lifes
Stable patterns that never change.

| Pattern | Description |
|---------|-------------|
| `block` | 2x2 square. The simplest still life. |
| `beehive` | 6-cell hexagonal shape. Very common in random soups. |
| `loaf` | 7-cell asymmetric still life. |
| `boat` | 5-cell still life with a pointed corner. |
| `tub` | 4-cell diamond. |

### Oscillators
Patterns that repeat with a fixed period.

| Pattern | Period | Description |
|---------|--------|-------------|
| `blinker` | 2 | Three cells in a line, alternating horizontal and vertical. The most common oscillator. |
| `toad` | 2 | Six-cell oscillator. Two offset rows of three. |
| `beacon` | 2 | Two touching 2x2 blocks that blink at their corner. |
| `pulsar` | 3 | 48-cell pattern with 4-fold symmetry. The most common period-3 oscillator. |
| `pentadecathlon` | 15 | 12-cell pattern with the longest period of any common oscillator. |

### Spaceships
Patterns that translate across the grid over time.
*(Placed facing left by default — use `]` in placement mode to rotate.)*

| Pattern | Speed | Cells | Description |
|---------|-------|-------|-------------|
| `glider` | c/4 diagonal | 5 | The smallest and most common spaceship. Discovered 1970. |
| `lwss` | c/2 orthogonal | 9 | Lightweight spaceship. |
| `mwss` | c/2 orthogonal | 11 | Middleweight spaceship. |
| `hwss` | c/2 orthogonal | 13 | Heavyweight spaceship. |
| `copperhead` | c/10 orthogonal | 28 | Discovered 2016 — surprisingly late for such a small ship. |

### Guns
Patterns that periodically emit spaceships.

| Pattern | Period | Description |
|---------|--------|-------------|
| `gosper_gun` | 30 | The first gun ever discovered (Bill Gosper, 1970). Emits a glider every 30 generations. 36 cells. |

### Methuselahs
Small patterns that take a very long time to stabilize.

| Pattern | Lifespan | Cells | Description |
|---------|----------|-------|-------------|
| `r_pentomino` | ~1000 gen | 5 | Deceptively simple — evolves chaotically for over 1000 generations before stabilizing. |
| `acorn` | ~5206 gen | 7 | One of the longest-lived small patterns known. |
| `diehard` | 130 gen | 7 | Disappears completely after exactly 130 generations. |

---

## Themes

| Theme | Description |
|-------|-------------|
| `green` | (default) |
| `yellow` | imitating an "amber" CRT monitor-style |
| `white` | Plain white on black |
| `rainbow` | Cell color cycles through the spectrum based on age |

Switch theme at runtime with `t`, or set at launch with `--theme NAME`.

---

## Saving

Saves are stored as JSON in `~/.life/`:

```json
{
  "gen": 42,
  "height": 48,
  "width": 190,
  "wrap": true,
  "cells": [[12, 34], [12, 35], ...]
}
```

Load the most recent save in-app with `l`, or load a specific file at launch:

```
python3 life.py --load ~/.life/state-1234567890.json
```

## Further reading 
    
https://www.scientificamerican.com/article/mathematical-games-1970-10/

https://www.nytimes.com/2020/12/28/science/math-conway-game-of-life.html

https://www.quantamagazine.org/john-conways-life-in-games-20150828/

https://alex.miller.garden/game-of-hope/

https://www.are.na/maxwell-neely-cohen/cellular-automata-amgeuasccxi
