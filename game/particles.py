"""Particle bursts + decaying screen shake. Honors the reduced_motion pref."""

from __future__ import annotations

import math
import random


class Particle:
    """One particle: pixel position, velocity in px/ms, life, color, size."""

    __slots__ = ("x", "y", "vx", "vy", "life_ms", "max_life", "color", "size")

    def __init__(self, x, y, vx, vy, life_ms, color, size):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life_ms = float(life_ms)
        self.max_life = float(life_ms)
        self.color = color
        self.size = float(size)


class ParticleSystem:
    """Particle list + screen shake timer. All timings in ms.

    reduced_motion disables both effects for accessibility: burst()/shatter()
    become no-ops, add_shake() is ignored and update() clears leftovers.
    """

    SHAKE_MS = 400.0
    SHAKE_MAX_PX = 8

    def __init__(self, reduced_motion=False):
        self.particles = []
        self.shake_ms = 0.0
        self.reduced_motion = bool(reduced_motion)

    # --- Emitters -----------------------------------------------------------
    def burst(self, x, y, color, count=12):
        """~12-particle burst at a pixel position (eat)."""
        if self.reduced_motion:
            return
        for _ in range(count):
            angle = random.random() * 2.0 * math.pi
            speed = random.random() * 0.10 + 0.05  # px/ms
            life = random.random() * 300.0 + 400.0
            size = random.random() * 2.0 + 2.0
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    life,
                    color,
                    size,
                )
            )

    def shatter(self, x, y, color, count=30):
        """Bigger 30-particle shatter on death."""
        self.burst(x, y, color, count=count)

    def add_shake(self, ms=None):
        """Start (or restart) the screen shake countdown."""
        if self.reduced_motion:
            return
        self.shake_ms = self.SHAKE_MS if ms is None else float(ms)

    # --- Update / draw ------------------------------------------------------
    def update(self, dt):
        dt = float(dt)
        if self.reduced_motion:
            self.particles.clear()
            self.shake_ms = 0.0
            return
        self.shake_ms = max(0.0, self.shake_ms - dt)
        if not self.particles:
            return
        keep = []
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.life_ms -= dt
            if particle.life_ms > 0.0:
                keep.append(particle)
        self.particles = keep

    def draw(self, surface):
        """Draw under the HUD; size shrinks as life decays."""
        import pygame

        for particle in self.particles:
            ratio = max(0.0, particle.life_ms / particle.max_life)
            radius = max(1, int(particle.size * (0.4 + 0.6 * ratio)))
            pygame.draw.circle(
                surface,
                particle.color,
                (int(particle.x), int(particle.y)),
                radius,
            )

    # --- Screen shake -------------------------------------------------------
    def shake_offset(self):
        """Random decaying (dx, dy) pixel offset for the grid origin."""
        if self.shake_ms <= 0.0 or self.reduced_motion:
            return (0, 0)
        amplitude = self.SHAKE_MAX_PX * (self.shake_ms / self.SHAKE_MS)
        dx = random.uniform(-amplitude, amplitude)
        dy = random.uniform(-amplitude, amplitude)
        return (int(dx), int(dy))
