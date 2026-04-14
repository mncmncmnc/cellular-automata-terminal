#!/usr/bin/env python3
"""
Conway's Game of Life in the terminal, mostly adapted from a bootleg 1990s Turbo Pascal version a friend pointed me to. Quick and dirty but I'm working on it.

Run:
    python3 life.py [options]

Bindings:
    arrows / hjkl   move cursor
    space           toggle cell under cursor
    enter           play / pause
    n or .          single step
    c               clear grid
    r               random fill (cycles 10% / 25% / 50%)
    p               pattern picker
    g               toggle grid lines
    b               toggle wrap / bounded edges
    + / -           faster / slower
    t               cycle theme (green / yellow / white / rainbow)
    s               save state
    l               load most recent save
    ?               help overlay
    q               quit
    
    Some selected readings for more info on Conway's Game of life-
    
    https://www.scientificamerican.com/article/mathematical-games-1970-10/
    
    https://www.nytimes.com/2020/12/28/science/math-conway-game-of-life.html
    
    https://www.quantamagazine.org/john-conways-life-in-games-20150828/
    
    https://alex.miller.garden/game-of-hope/
    
    https://www.are.na/maxwell-neely-cohen/cellular-automata-amgeuasccxi
    
"""

import argparse
import curses
import json
import random
import time
from pathlib import Path


# Patterns

def _parse(s):
    """Multi-line string → list[(row, col)]. 'O' / '#' / 'X' are alive."""
    cells = []
    for r, line in enumerate(s.strip('\n').splitlines()):
        for c, ch in enumerate(line):
            if ch in 'O#X':
                cells.append((r, c))
    return cells


def _normalize(pairs):
    """Shift a list of (row, col) tuples so the min row/col is (0, 0)."""
    if not pairs:
        return []
    mr = min(r for r, _ in pairs)
    mc = min(c for _, c in pairs)
    return [(r - mr, c - mc) for r, c in pairs]


PATTERNS = {
    # Still lifes
    'block': _parse("""
##
##
"""),
    'beehive': _parse("""
.##.
#..#
.##.
"""),
    'loaf': _parse("""
.##.
#..#
.#.#
..#.
"""),
    'boat': _parse("""
##.
#.#
.#.
"""),
    'tub': _parse("""
.#.
#.#
.#.
"""),

    # Oscillators
    'blinker': _parse("""
###
"""),
    'toad': _parse("""
.###
###.
"""),
    'beacon': _parse("""
##..
##..
..##
..##
"""),
    'pulsar': _parse("""
..###...###..
.............
#....#.#....#
#....#.#....#
#....#.#....#
..###...###..
.............
..###...###..
#....#.#....#
#....#.#....#
#....#.#....#
.............
..###...###..
"""),
    'pentadecathlon': _parse("""
..#....#..
##.####.##
..#....#..
"""),

    # Spaceships
    'glider': _parse("""
.#.
..#
###
"""),
    'lwss': _parse("""
.#..#
#....
#...#
####.
"""),
    'mwss': _parse("""
...#..
.#...#
#.....
#....#
#####.
"""),
    'hwss': _parse("""
...##..
.#....#
#......
#.....#
######.
"""),
    'copperhead': _parse("""
.##..##.
...##...
...##...
#.#..#.#
#......#
........
#......#
.##..##.
..####..
........
...##...
...##...
"""),

    # Guns
    'gosper_gun': _normalize([
        (4, 0), (4, 1), (5, 0), (5, 1),
        (4, 10), (5, 10), (6, 10),
        (3, 11), (7, 11),
        (2, 12), (2, 13),
        (8, 12), (8, 13),
        (5, 14),
        (3, 15), (7, 15),
        (4, 16), (5, 16), (6, 16),
        (5, 17),
        (2, 20), (3, 20), (4, 20),
        (2, 21), (3, 21), (4, 21),
        (1, 22), (5, 22),
        (0, 24), (1, 24), (5, 24), (6, 24),
        (2, 34), (3, 34),
        (2, 35), (3, 35),
    ]),

    # Methuselahs
    'r_pentomino': _parse("""
.##
##.
.#.
"""),
    'acorn': _parse("""
.#.....
...#...
##..###
"""),
    'diehard': _parse("""
......#.
##......
.#...###
"""),
}


CATEGORIES = [
    ('Still lifes',  ['block', 'beehive', 'loaf', 'boat', 'tub']),
    ('Oscillators',  ['blinker', 'toad', 'beacon', 'pulsar', 'pentadecathlon']),
    ('Spaceships',   ['glider', 'lwss', 'mwss', 'hwss', 'copperhead']),
    ('Guns',         ['gosper_gun']),
    ('Methuselahs',  ['r_pentomino', 'acorn', 'diehard']),
]


def rotate_ccw(coords, times=1):
    """Rotate a pattern 90° counter-clockwise `times` times. Returns normalize-d list."""
    out = list(coords)
    for _ in range(times % 4):
        out = [(-c, r) for r, c in out]
    return _normalize(out)


# Themes

THEMES = ['green', 'yellow', 'white', 'rainbow']


# Life engine

class Life:
    def __init__(self, height, width, wrap=True):
        self.height = height
        self.width = width
        self.wrap = wrap
        self.cells = set()         # set[(row, col)]
        self.ages = {}             # (row, col) -> generations alive
        self.gen = 0

    def clear(self):
        self.cells.clear()
        self.ages.clear()
        self.gen = 0

    def in_bounds(self, r, c):
        return 0 <= r < self.height and 0 <= c < self.width

    def set_cell(self, r, c, alive=True):
        if not self.in_bounds(r, c):
            return
        if alive:
            if (r, c) not in self.cells:
                self.cells.add((r, c))
                self.ages[(r, c)] = 0
        else:
            self.cells.discard((r, c))
            self.ages.pop((r, c), None)

    def toggle(self, r, c):
        if (r, c) in self.cells:
            self.set_cell(r, c, False)
        else:
            self.set_cell(r, c, True)

    def random_fill(self, density):
        self.clear()
        for r in range(self.height):
            for c in range(self.width):
                if random.random() < density:
                    self.cells.add((r, c))
                    self.ages[(r, c)] = 0

    def stamp(self, pattern, row, col, rotation=0):
        """Stamp a pattern anchored so its center lands near (row, col)."""
        coords = rotate_ccw(pattern, rotation)
        if not coords:
            return
        h = max(r for r, _ in coords) + 1
        w = max(c for _, c in coords) + 1
        r0 = row - h // 2
        c0 = col - w // 2
        for dr, dc in coords:
            self.set_cell(r0 + dr, c0 + dc)

    def _neighbor_offsets(self):
        return ((-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1))

    def step(self):
        counts = {}
        H, W = self.height, self.width
        wrap = self.wrap
        for (r, c) in self.cells:
            for dr, dc in self._neighbor_offsets():
                nr, nc = r + dr, c + dc
                if wrap:
                    nr %= H
                    nc %= W
                elif not (0 <= nr < H and 0 <= nc < W):
                    continue
                counts[(nr, nc)] = counts.get((nr, nc), 0) + 1

        new_cells = set()
        new_ages = {}
        for pos, n in counts.items():
            if n == 3 or (n == 2 and pos in self.cells):
                new_cells.add(pos)
                new_ages[pos] = self.ages.get(pos, -1) + 1
        self.cells = new_cells
        self.ages = new_ages
        self.gen += 1

    def population(self):
        return len(self.cells)

    def to_dict(self):
        return {
            'gen': self.gen,
            'height': self.height,
            'width': self.width,
            'wrap': self.wrap,
            'cells': sorted([r, c] for r, c in self.cells),
        }

    @classmethod
    def from_dict(cls, d):
        life = cls(int(d['height']), int(d['width']), bool(d.get('wrap', True)))
        life.gen = int(d.get('gen', 0))
        for r, c in d['cells']:
            life.cells.add((int(r), int(c)))
            life.ages[(int(r), int(c))] = 0
        return life


# UI

HELP_LINES = [
    "GAME OF LIFE - help",
    "",
    "  arrows / hjkl   move cursor",
    "  space           toggle cell under cursor",
    "  enter           play / pause",
    "  n or .          single step",
    "  c               clear grid",
    "  r               random fill (10/25/50%)",
    "  p               pattern picker",
    "  g               toggle grid lines",
    "  b               toggle wrap / bounded edges",
    "  + / -           speed up / down",
    "  t               cycle theme",
    "  s               save state",
    "  l               load most recent save",
    "  ?               this help",
    "  q               quit",
    "",
    "  press any key to close",
]


class UI:
    def __init__(self, stdscr, life, theme='green', show_grid=True, speed=10):
        self.stdscr = stdscr
        self.life = life
        self.theme_name = theme if theme in THEMES else 'green'
        self.show_grid = show_grid
        self.speed = max(1, min(60, speed))
        self.running = False
        self.cursor = [life.height // 2, life.width // 2]
        self.random_densities = [0.10, 0.25, 0.50]
        self.density_idx = 0
        self.message = ""
        self.message_until = 0.0
        self._init_colors()

    # colors

    def _init_colors(self):
        self.color_ok = False
        if not curses.has_colors():
            self.theme_name = 'white'
            self._build_palette_no_color()
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        self.color_ok = True
        self._build_palette()

    def _build_palette_no_color(self):
        # pair_num[color_idx] — index 0 = dead (unused), 1+ = alive
        self.color_pairs = [0, 0]  # fallback to default pair

    def _build_palette(self):
        if self.theme_name == 'rainbow':
            colors = [
                curses.COLOR_RED,
                curses.COLOR_YELLOW,
                curses.COLOR_GREEN,
                curses.COLOR_CYAN,
                curses.COLOR_BLUE,
                curses.COLOR_MAGENTA,
            ]
        elif self.theme_name == 'yellow':
            colors = [curses.COLOR_YELLOW]
        elif self.theme_name == 'white':
            colors = [curses.COLOR_WHITE]
        else:  # green
            colors = [curses.COLOR_GREEN]

        # color_pairs[0] = dead (pair 0 = default), color_pairs[1..n] = alive hues.
        # Each alive pair: fg=color, bg=color -- solid colored block when drawing ' '.
        self.color_pairs = [0]  # index 0 = dead
        for i, color in enumerate(colors):
            pair_num = i + 1
            try:
                curses.init_pair(pair_num, color, color)
                self.color_pairs.append(pair_num)
            except curses.error:
                self.color_pairs.append(0)

    def cycle_theme(self):
        idx = THEMES.index(self.theme_name)
        self.theme_name = THEMES[(idx + 1) % len(THEMES)]
        if self.color_ok:
            self._build_palette()
        else:
            self._build_palette_no_color()
        self.flash(f"theme: {self.theme_name}")

    def _age_color(self, age):
        n = len(self.color_pairs) - 1  # number of alive hues
        if self.theme_name == 'rainbow' and n > 1:
            return (age // 4) % n + 1
        return 1

    # layout

    def _viewport(self):
        H, W = self.stdscr.getmaxyx()
        usable_term_rows = max(1, H - 1)
        grid_rows = min(self.life.height, usable_term_rows)
        grid_cols = min(self.life.width, max(1, W - 1))
        top = max(0, self.cursor[0] - grid_rows // 2)
        top = min(top, self.life.height - grid_rows)
        top = max(0, top)
        left = max(0, self.cursor[1] - grid_cols // 2)
        left = min(left, self.life.width - grid_cols)
        left = max(0, left)
        return grid_rows, grid_cols, top, left

    # rendering

    def render(self):
        H, W = self.stdscr.getmaxyx()
        if H < 6 or W < 20:
            self.stdscr.erase()
            try:
                self.stdscr.addstr(0, 0, "terminal too small")
            except curses.error:
                pass
            self.stdscr.refresh()
            return

        self.stdscr.erase()
        self._draw_grid()
        self._draw_cursor()
        self._draw_status_bar()
        self.stdscr.refresh()

    def _draw_grid(self):
        gr, gc, top, left = self._viewport()
        cells = self.life.cells
        ages = self.life.ages
        for tr in range(gr):
            row = top + tr
            for tc in range(gc):
                col = left + tc
                if (row, col) not in cells:
                    if self.show_grid and (tr % 4 == 0) and (tc % 8 == 0):
                        try:
                            self.stdscr.addstr(tr, tc, '.', curses.A_DIM)
                        except curses.error:
                            pass
                    continue
                color_idx = self._age_color(ages.get((row, col), 0))
                pair = self.color_pairs[color_idx] if color_idx < len(self.color_pairs) else 0
                try:
                    self.stdscr.addstr(tr, tc, ' ', curses.color_pair(pair))
                except curses.error:
                    pass

    def _draw_cursor(self):
        if self.running:
            return
        gr, gc, top, left = self._viewport()
        cr, cc = self.cursor
        if not (top <= cr < top + gr and left <= cc < left + gc):
            return
        term_r = cr - top
        term_c = cc - left
        try:
            self.stdscr.chgat(term_r, term_c, 1, curses.A_REVERSE)
        except curses.error:
            pass

    def _draw_status_bar(self):
        H, W = self.stdscr.getmaxyx()
        state = 'RUNNING' if self.running else 'PAUSED'
        edges = 'wrap' if self.life.wrap else 'bounded'
        base = (
            f" gen {self.life.gen:>5}  pop {self.life.population():>5} "
            f" {self.speed:>2}/s  {edges}  {self.theme_name}  {state} "
        )
        if time.time() < self.message_until and self.message:
            base = f" {self.message} "
        text = base.ljust(W)[: W - 1]
        try:
            self.stdscr.addstr(H - 1, 0, text, curses.A_REVERSE)
        except curses.error:
            pass

    def flash(self, text, dur=1.5):
        self.message = text
        self.message_until = time.time() + dur

    # overlays

    def show_help(self):
        self._draw_box(HELP_LINES)
        self.stdscr.refresh()
        self.stdscr.nodelay(False)
        self.stdscr.getch()
        self.stdscr.nodelay(True)

    def _draw_box(self, lines, highlight_idx=None):
        H, W = self.stdscr.getmaxyx()
        box_w = min(W - 2, max(len(line) for line in lines) + 4)
        box_h = min(H - 2, len(lines) + 2)
        top = max(0, (H - box_h) // 2)
        left = max(0, (W - box_w) // 2)
        border_top = '+' + '-' * (box_w - 2) + '+'
        try:
            self.stdscr.addstr(top, left, border_top)
            self.stdscr.addstr(top + box_h - 1, left, border_top)
        except curses.error:
            pass
        for i in range(box_h - 2):
            row = top + 1 + i
            line = lines[i] if i < len(lines) else ''
            content = '| ' + line.ljust(box_w - 4)[: box_w - 4] + ' |'
            attr = curses.A_REVERSE if highlight_idx is not None and i == highlight_idx else 0
            try:
                self.stdscr.addstr(row, left, content, attr)
            except curses.error:
                pass

    def pattern_picker(self):
        items = []  # list of (label, name_or_None_for_header)
        for cat, names in CATEGORIES:
            items.append((f"-- {cat} --", None))
            for n in names:
                items.append((f"  {n}", n))
        # selectable index
        idx = next((i for i, it in enumerate(items) if it[1] is not None), 0)

        self.stdscr.nodelay(False)
        try:
            while True:
                lines = ["PATTERN PICKER", ""]
                for i, (label, _) in enumerate(items):
                    prefix = '> ' if i == idx else '  '
                    lines.append(prefix + label)
                lines.append("")
                lines.append("up/down select  enter pick  esc/q cancel")
                self._draw_box(lines)
                self.stdscr.refresh()
                k = self.stdscr.getch()
                if k in (curses.KEY_UP, ord('k')):
                    new = idx - 1
                    while new >= 0 and items[new][1] is None:
                        new -= 1
                    if new >= 0:
                        idx = new
                elif k in (curses.KEY_DOWN, ord('j')):
                    new = idx + 1
                    while new < len(items) and items[new][1] is None:
                        new += 1
                    if new < len(items):
                        idx = new
                elif k in (10, 13, curses.KEY_ENTER):
                    return items[idx][1]
                elif k in (27, ord('q')):
                    return None
        finally:
            self.stdscr.nodelay(True)

    def place_pattern(self, name):
        """Placement: arrows move, [ / ] rotate, enter stamp, esc cancel."""
        pattern = PATTERNS[name]
        rotation = 0
        r, c = self.life.height // 2, self.life.width // 2

        self.stdscr.nodelay(False)
        try:
            while True:
                self.stdscr.erase()
                self._draw_grid()
                self._draw_ghost(pattern, r, c, rotation)

                H, W = self.stdscr.getmaxyx()
                hint = (
                    f" place {name}  arrows/hjkl move  [ / ] rotate "
                    f" enter stamp  esc cancel "
                )
                text = hint.ljust(W)[: W - 1]
                try:
                    self.stdscr.addstr(H - 1, 0, text, curses.A_REVERSE)
                except curses.error:
                    pass
                self.stdscr.refresh()

                k = self.stdscr.getch()
                if k in (curses.KEY_LEFT, ord('h')):
                    c = max(0, c - 1)
                elif k in (curses.KEY_RIGHT, ord('l')):
                    c = min(self.life.width - 1, c + 1)
                elif k in (curses.KEY_UP, ord('k')):
                    r = max(0, r - 1)
                elif k in (curses.KEY_DOWN, ord('j')):
                    r = min(self.life.height - 1, r + 1)
                elif k == ord('['):
                    rotation = (rotation + 1) % 4
                elif k == ord(']'):
                    rotation = (rotation + 3) % 4
                elif k in (10, 13, curses.KEY_ENTER):
                    self.life.stamp(pattern, r, c, rotation)
                    self.flash(f"stamped {name}")
                    return
                elif k in (27, ord('q')):
                    return
        finally:
            self.stdscr.nodelay(True)

    def _draw_ghost(self, pattern, row, col, rotation):
        coords = rotate_ccw(pattern, rotation)
        if not coords:
            return
        h = max(r for r, _ in coords) + 1
        w = max(c for _, c in coords) + 1
        r0 = row - h // 2
        c0 = col - w // 2
        gr, gc, top, left = self._viewport()
        for dr, dc in coords:
            gy = r0 + dr
            gx = c0 + dc
            if not (top <= gy < top + gr and left <= gx < left + gc):
                continue
            term_r = gy - top
            term_c = gx - left
            try:
                self.stdscr.chgat(term_r, term_c, 1, curses.A_REVERSE)
            except curses.error:
                pass

    # save / load

    def _save_dir(self):
        p = Path.home() / '.life'
        p.mkdir(parents=True, exist_ok=True)
        return p

    def save(self):
        try:
            p = self._save_dir() / f"state-{int(time.time())}.json"
            with p.open('w') as f:
                json.dump(self.life.to_dict(), f)
            self.flash(f"saved {p.name}")
        except OSError as e:
            self.flash(f"save failed: {e}")

    def load(self):
        d = self._save_dir()
        files = sorted(d.glob('state-*.json'))
        if not files:
            self.flash("no saves found")
            return
        try:
            with files[-1].open() as f:
                data = json.load(f)
            self.life = Life.from_dict(data)
            self.cursor = [self.life.height // 2, self.life.width // 2]
            self.flash(f"loaded {files[-1].name}")
        except (OSError, ValueError, KeyError) as e:
            self.flash(f"load failed: {e}")

    # actions

    def move_cursor(self, dr, dc):
        self.cursor[0] = max(0, min(self.life.height - 1, self.cursor[0] + dr))
        self.cursor[1] = max(0, min(self.life.width - 1, self.cursor[1] + dc))

    def random_fill(self):
        d = self.random_densities[self.density_idx]
        self.life.random_fill(d)
        self.flash(f"random fill {int(d * 100)}%")
        self.density_idx = (self.density_idx + 1) % len(self.random_densities)

    # main loop

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        last_step = time.time()
        while True:
            now = time.time()
            if self.running:
                interval = 1.0 / self.speed
                if now - last_step >= interval:
                    self.life.step()
                    last_step = now
                self.render()
                # Sleep until next step (or input)
                remaining = interval - (time.time() - last_step)
                timeout_ms = max(1, int(remaining * 1000))
                self.stdscr.timeout(timeout_ms)
            else:
                self.render()
                self.stdscr.timeout(100)  # 10 Hz refresh when paused

            k = self.stdscr.getch()
            if k == -1:
                continue
            if k == curses.KEY_RESIZE:
                continue

            if k == ord('q'):
                return
            elif k in (10, 13, curses.KEY_ENTER):
                self.running = not self.running
                last_step = time.time()
            elif k == ord(' '):
                self.life.toggle(*self.cursor)
            elif k in (ord('n'), ord('.')):
                if not self.running:
                    self.life.step()
            elif k == ord('c'):
                self.life.clear()
                self.flash("cleared")
            elif k == ord('r'):
                self.random_fill()
            elif k == ord('p'):
                self.running = False
                name = self.pattern_picker()
                if name:
                    self.place_pattern(name)
            elif k == ord('g'):
                self.show_grid = not self.show_grid
                self.flash(f"grid {'on' if self.show_grid else 'off'}")
            elif k == ord('b'):
                self.life.wrap = not self.life.wrap
                self.flash(f"edges: {'wrap' if self.life.wrap else 'bounded'}")
            elif k in (ord('+'), ord('=')):
                self.speed = min(60, self.speed + 1)
            elif k == ord('-'):
                self.speed = max(1, self.speed - 1)
            elif k == ord('t'):
                self.cycle_theme()
            elif k == ord('s'):
                self.save()
            elif k == ord('l'):
                self.load()
            elif k == ord('?'):
                self.running = False
                self.show_help()
            elif k == curses.KEY_LEFT or k == ord('h'):
                self.move_cursor(0, -1)
            elif k == curses.KEY_RIGHT or k == ord('l'):
                self.move_cursor(0, 1)
            elif k == curses.KEY_UP or k == ord('k'):
                self.move_cursor(-1, 0)
            elif k == curses.KEY_DOWN or k == ord('j'):
                self.move_cursor(1, 0)


# CLI

def list_patterns():
    for cat, names in CATEGORIES:
        print(f"{cat}:")
        for n in names:
            print(f"  {n}")


def build_life(args, stdscr=None):
    # Determine grid size or auto-fit to terminal
    if stdscr is not None:
        H, W = stdscr.getmaxyx()
        auto_h = max(10, H - 1)
        auto_w = max(20, W - 1)
    else:
        auto_h, auto_w = 60, 160

    height = args.height or auto_h
    width = args.width or auto_w
    life = Life(height, width, wrap=not args.bounded)

    if args.load:
        try:
            with open(args.load) as f:
                data = json.load(f)
            life = Life.from_dict(data)
        except Exception as e:
            print(f"load failed: {e}")
            raise SystemExit(1)
    elif args.pattern:
        if args.pattern not in PATTERNS:
            print(f"unknown pattern: {args.pattern}")
            print("run with --list-patterns to see available patterns")
            raise SystemExit(1)
        life.stamp(PATTERNS[args.pattern], life.height // 2, life.width // 2)
    elif args.random is not None:
        life.random_fill(max(0.0, min(1.0, args.random / 100.0)))

    return life


def _curses_main(stdscr, args):
    life = build_life(args, stdscr)
    ui = UI(
        stdscr,
        life,
        theme=args.theme,
        show_grid=not args.no_grid,
        speed=args.speed,
    )
    ui.run()


def main():
    parser = argparse.ArgumentParser(
        prog='life',
        description="Conway's Game of Life in the terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Keys: arrows/hjkl move, space toggle, enter play, p patterns, ? help, q quit",
    )
    parser.add_argument('--pattern', metavar='NAME',
                        help='start with a centered pattern (see --list-patterns)')
    parser.add_argument('--random', metavar='PCT', type=float,
                        help='random-fill at this density (0-100)')
    parser.add_argument('--speed', metavar='N', type=int, default=10,
                        help='initial generations per second (1-60, default 10)')
    parser.add_argument('--theme', choices=THEMES, default='green',
                        help='color theme (default: green)')
    parser.add_argument('--no-grid', action='store_true',
                        help='start with grid lines off')
    parser.add_argument('--bounded', action='store_true',
                        help='use bounded edges instead of wrap')
    parser.add_argument('--width', type=int, help='grid width (default: terminal)')
    parser.add_argument('--height', type=int, help='grid height (default: terminal rows)')
    parser.add_argument('--load', metavar='FILE', help='load a saved JSON state')
    parser.add_argument('--list-patterns', action='store_true',
                        help='print all pattern names and exit')
    args = parser.parse_args()

    if args.list_patterns:
        list_patterns()
        return

    curses.wrapper(_curses_main, args)


if __name__ == '__main__':
    main()

#todo -> add day+night and seeds 