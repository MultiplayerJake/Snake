"""Menu demo: an AI snake playing in the background (walls wrap, no death).

BFS shortest path to the apple avoiding the body; falls back to follow-tail
when no safe path exists. Reuses Snake/Apple on the same grid and runs on a
slower tick (12 ticks per move). Lives only on the menu screen: the main loop
calls update() on the active state, so the demo pauses automatically whenever
another screen is shown.
"""

from __future__ import annotations

from collections import deque

from game.apple import Apple
from game.constants import GRID_SIZE
from game.snake import Snake

DEMO_TICKS = 12  # frames per move @60fps (slower than gameplay)
DEMO_RESET_LENGTH = GRID_SIZE * GRID_SIZE // 3  # keep the demo from filling up


def grid_metrics(w, h):
    """(cell, origin_x, hud_h): shared layout math for full-height grids."""
    hud_h = max(40, h // 12)
    cell = max(8, (h - hud_h) // GRID_SIZE)
    origin_x = (w - cell * GRID_SIZE) // 2
    return cell, origin_x, hud_h


def _neighbors(cell, wrap):
    col, row = cell
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nc, nr = col + dx, row + dy
        if wrap:
            nc %= GRID_SIZE
            nr %= GRID_SIZE
        elif not (0 <= nc < GRID_SIZE and 0 <= nr < GRID_SIZE):
            continue
        yield (nc, nr)


def bfs_path(start, goal, blocked, wrap=False):
    """Shortest path from start to goal as a list of cells (excl. start).

    Returns None when no path exists. `blocked` is a set of cells to avoid.
    """
    if start == goal:
        return None
    queue = deque([start])
    parents = {start: None}
    while queue:
        cell = queue.popleft()
        for nxt in _neighbors(cell, wrap):
            if nxt in parents or nxt in blocked:
                continue
            parents[nxt] = cell
            if nxt == goal:
                path = [nxt]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                path.reverse()
                return path[1:]
            queue.append(nxt)
    return None


def _direction_between(a, b):
    """Grid step from a to b, tolerant of wrap-around (demo only)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx > 1:
        dx = -1
    elif dx < -1:
        dx = 1
    if dy > 1:
        dy = -1
    elif dy < -1:
        dy = 1
    return (dx, dy)


class DemoSnake:
    """A tiny AI-driven game for the menu background. Walls wrap; no death."""

    def __init__(self):
        self.acc = 0.0
        self.reset()

    @property
    def step_ms(self):
        return DEMO_TICKS * (1000.0 / 60.0)

    def reset(self):
        self.snake = Snake()
        self.apple = Apple()
        self.apple.respawn(self.snake.body)

    def update(self, dt):
        """Advance the demo; runs only while the menu screen is active."""
        self.acc += float(dt)
        guard = 0
        while self.acc >= self.step_ms and guard < 8:
            self.acc -= self.step_ms
            self.step()
            guard += 1

    def step(self):
        direction = self._choose_direction()
        if direction is None:
            # Stuck: the head is sealed inside its own body - no path to the
            # apple and no path to the tail. Every move would step onto a
            # body cell (the demo has no death, so nothing would catch it),
            # corrupting the body with duplicates. Plan 22: auto-reset when
            # stuck instead of moving.
            self.reset()
            return
        if direction != (
            -self.snake.direction[0],
            -self.snake.direction[1],
        ):
            self.snake.direction = direction
            self.snake.pending_dir = None
        head = self.snake.step()
        # Walls wrap in the demo: fold the head back into the grid.
        col, row = head
        self.snake.body[0] = (col % GRID_SIZE, row % GRID_SIZE)
        if self.snake.body[0] == self.apple.pos:
            self.snake.grow_by += 1
            if (
                not self.apple.respawn(self.snake.body)
                or len(self.snake.body) > DEMO_RESET_LENGTH
            ):
                self.reset()

    def _choose_direction(self):
        head = self.snake.body[0]
        path = bfs_path(
            head, self.apple.pos, blocked=set(self.snake.body[1:]), wrap=True
        )
        if path:
            return _direction_between(head, path[0])
        # No safe path to the apple: follow the tail to stay alive.
        tail = self.snake.body[-1]
        blocked = set(self.snake.body[1:-1])
        if self.snake.grow_by > 0:
            blocked.add(tail)  # tail won't vacate this step while growing
        path = bfs_path(head, tail, blocked=blocked, wrap=True)
        if path:
            return _direction_between(head, path[0])
        return None  # stuck: caller auto-resets (plan 22)

    def draw(self, surface, origin_x, origin_y, cell):
        self.apple.draw(surface, origin_x, origin_y, cell)
        self.snake.draw(surface, origin_x, origin_y, cell, alpha=1.0)
