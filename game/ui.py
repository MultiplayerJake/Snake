"""Reusable UI widgets + neon drawing helpers (single Cyber palette).

Widgets read colors from game.themes.get_theme(); with the palette fixed to
Cyber (Task 24) every widget renders as a dark panel with glowing cyan/magenta
neon outlines without knowing anything about themes. Also home to the shared
neon primitives: alpha glow shapes, halo text, the play-grid frame and the
GlitchTitle used by the main menu (Task 26).

Fonts are monospace/techy (consolas first, then other mono faces) so numbers
line up in the HUD and keybind boxes.
"""

from __future__ import annotations

import random

import pygame

from game.constants import (
    ACTION_LABELS,
    key_label,
    lerp_color,
)
from game.themes import get_theme

# --- Fonts (monospace / techy) -----------------------------------------------

_font_cache = {}

# First match wins: consolas on Windows, then common cross-platform monos.
_MONO_CANDIDATES = (
    "consolas",
    "couriernew",
    "dejavusansmono",
    "menlo",
    "monaco",
    "segoeui",
    "arial",
)


def get_font(size, bold=False):
    """Cached font lookup; scales with cell/HUD sizes computed by callers."""
    size = max(8, int(round(size)))
    key = (size, bold)
    font = _font_cache.get(key)
    if font is None:
        path = None
        for candidate in _MONO_CANDIDATES:
            try:
                path = pygame.font.match_font(candidate)
            except Exception:
                path = None
            if path:
                break
        try:
            font = pygame.font.Font(path, size)
        except Exception:
            font = pygame.font.Font(None, size)
        if bold:
            try:
                font.set_bold(True)
            except Exception:
                pass
        _font_cache[key] = font
    return font


def draw_text(surface, text, size, color, pos, anchor="center", bold=False, shadow=None):
    """Render one line of text with an anchor point (e.g. 'midleft')."""
    font = get_font(size, bold)
    try:
        image = font.render(str(text), True, color)
    except Exception:
        return None
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    if shadow is not None:
        shadow_image = font.render(str(text), True, shadow)
        shadow_rect = shadow_image.get_rect()
        setattr(shadow_rect, anchor, (pos[0] + 2, pos[1] + 2))
        surface.blit(shadow_image, shadow_rect)
    surface.blit(image, rect)
    return rect


def draw_neon_text(surface, text, size, color, pos, anchor="center", bold=True,
                   bg=None, spread=None):
    """Neon text: a dim halo in four directions, crisp color on top.

    `bg` is the color the halo blends toward (defaults to the palette bg),
    `spread` defaults to roughly size/24 so big headings glow wider.
    """
    font = get_font(size, bold)
    try:
        image = font.render(str(text), True, color)
    except Exception:
        return None
    base = image.get_rect()
    setattr(base, anchor, pos)
    if bg is None:
        bg = get_theme()["bg"]
    try:
        halo_image = font.render(str(text), True, lerp_color(color, bg, 0.55))
        if spread is None:
            spread = max(2, int(size) // 24)
        for dx, dy in ((spread, 0), (-spread, 0), (0, spread), (0, -spread)):
            surface.blit(halo_image, base.move(dx, dy))
    except Exception:
        pass
    surface.blit(image, base)
    return base


def fit_text(font, text, max_width):
    """Truncate text with an ellipsis so it fits inside max_width pixels."""
    text = str(text)
    try:
        if font.size(text)[0] <= max_width:
            return text
    except Exception:
        return text
    while text:
        text = text[:-1]
        candidate = text.rstrip() + "..."
        try:
            if font.size(candidate)[0] <= max_width:
                return candidate
        except Exception:
            return candidate
    return ""


# --- Neon primitives ---------------------------------------------------------

def draw_glow_rect(surface, color, rect, radius=0, alpha=60, grow=6):
    """Soft alpha-blended neon glow under a rounded rect (pseudocode 29)."""
    rect = pygame.Rect(rect)
    glow = rect.inflate(grow * 2, grow * 2)
    if glow.w <= 1 or glow.h <= 1:
        return
    layer = pygame.Surface((glow.w, glow.h), pygame.SRCALPHA)
    pygame.draw.rect(
        layer,
        (int(color[0]), int(color[1]), int(color[2]), int(alpha)),
        layer.get_rect(),
        border_radius=max(0, int(radius) + int(grow)),
    )
    surface.blit(layer, glow.topleft)


def draw_glow_circle(surface, color, center, radius, alpha=60, grow=4):
    """Soft alpha-blended neon glow under a circle (apples, antenna nodes)."""
    radius = int(radius)
    if radius < 1:
        return
    total = radius + max(0, int(grow))
    layer = pygame.Surface((total * 2, total * 2), pygame.SRCALPHA)
    pygame.draw.circle(
        layer,
        (int(color[0]), int(color[1]), int(color[2]), int(alpha)),
        (total, total),
        total,
    )
    surface.blit(layer, (int(center[0]) - total, int(center[1]) - total))


def draw_neon_frame(surface, rect, inner=True):
    """Glowing magenta/cyan border frame around the 25x25 play grid (Task 24).

    Outer magenta stroke + inner cyan hairline over a soft two-stage alpha
    glow; all derived from the rect so it works at any resolution.
    """
    theme = get_theme()
    magenta = theme["neon_magenta"]
    cyan = theme["neon_cyan"]
    rect = pygame.Rect(rect)
    if rect.w < 4 or rect.h < 4:
        return
    pad = 8
    layer = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
    try:
        pygame.draw.rect(
            layer, (*magenta, 38),
            pygame.Rect(pad - 4, pad - 4, rect.w + 8, rect.h + 8),
            width=6, border_radius=10,
        )
        pygame.draw.rect(
            layer, (*magenta, 70),
            pygame.Rect(pad - 2, pad - 2, rect.w + 4, rect.h + 4),
            width=4, border_radius=9,
        )
    except (ValueError, TypeError):
        pass
    surface.blit(layer, (rect.x - pad, rect.y - pad))
    pygame.draw.rect(surface, magenta, rect, width=2, border_radius=8)
    if inner:
        pygame.draw.rect(surface, cyan, rect.inflate(-4, -4), width=1, border_radius=6)


# --- Centralized button click SFX (Task 29) -----------------------------------

# AudioManager registers itself here at init; widgets never import game.audio
# (no circular imports) and a missing mixer/broken file stays a silent no-op.
_click_sound = None


def set_click_sound(callback):
    """Register the callable fired on every Button press (None to disable)."""
    global _click_sound
    _click_sound = callback


def _fire_click_sound():
    cb = _click_sound
    if cb is None:
        return
    try:
        cb()
    except Exception:
        pass  # audio must never break a button press


# --- Widgets -----------------------------------------------------------------

class Button:
    """Clickable neon button (Task 26): dark fill + glowing cyan outline.

    hover/pressed -> brighter, thicker outline plus two glow underlays
    (alpha 45/80); pressed -> magenta outline; accent -> primary button
    (magenta outline + tinted fill); active -> selected state (tinted fill +
    cyan outline). Callback fires on mouse-down, like the old widget, and the
    centralized click SFX fires first on every press (Task 29) so menu, mode
    picker, settings and pause/game-over overlays all inherit it.
    """

    def __init__(self, rect, label, callback, accent=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.accent = accent
        self.active = False
        self.hovered = False
        self.pressed = False

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and getattr(event, "button", 0) == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.pressed = True
            _fire_click_sound()
            self.callback()
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False
        return False

    def draw(self, surface):
        theme = get_theme()
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        hot = self.hovered or self.pressed
        if self.active:
            base = theme["button_accent_hover"] if hot else theme["button_accent"]
            border = theme["neon_cyan"]
            text_color = theme["text"]
        elif self.accent:
            base = theme["button_accent_hover"] if hot else theme["button_accent"]
            border = theme["neon_magenta"]
            text_color = theme["text"]
        else:
            base = theme["button_hover"] if self.hovered else theme["button"]
            border = theme["neon_magenta"] if self.pressed else theme["neon_cyan"]
            text_color = theme["neon_cyan"]
        radius = max(4, self.rect.h // 4)
        # Glow underlays: two inflated rects, brighter when hot.
        if hot or self.accent or self.active:
            draw_glow_rect(surface, border, self.rect, radius,
                           alpha=80 if hot else 45, grow=7)
            draw_glow_rect(surface, border, self.rect, radius,
                           alpha=45 if hot else 25, grow=3)
        pygame.draw.rect(surface, base, self.rect, border_radius=radius)
        pygame.draw.rect(surface, border, self.rect, width=3 if hot else 2,
                         border_radius=radius)
        draw_neon_text(surface, self.label, self.rect.h * 0.42, text_color,
                       self.rect.center, "center", bg=base)


class Slider:
    """Horizontal 0..1 slider. on_change fires live, on_commit on release."""

    def __init__(self, rect, value=0.5, on_change=None, on_commit=None):
        self.rect = pygame.Rect(rect)
        self.value = min(1.0, max(0.0, float(value)))
        self.on_change = on_change
        self.on_commit = on_commit
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
            if self.dragging:
                self.dragging = False
                if self.on_commit is not None:
                    self.on_commit()
                return True
        return False

    def _set_from_x(self, x):
        if self.rect.w <= 0:
            return
        self.value = min(1.0, max(0.0, (x - self.rect.x) / self.rect.w))
        if self.on_change is not None:
            self.on_change(self.value)

    def draw(self, surface):
        theme = get_theme()
        track_h = max(4, self.rect.h // 5)
        track = pygame.Rect(self.rect.x, self.rect.centery - track_h // 2, self.rect.w, track_h)
        radius = track_h // 2
        pygame.draw.rect(surface, theme["slider_track"], track, border_radius=radius)
        fill_w = int(track.w * self.value)
        fill = track.copy()
        fill.w = max(radius * 2, fill_w)
        pygame.draw.rect(surface, theme["accent_dark"], fill, border_radius=radius)
        knob_r = max(6, self.rect.h // 3)
        knob_cx = track.x + fill_w
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        knob_color = theme["accent"] if (hovered or self.dragging) else theme["text"]
        pygame.draw.circle(surface, theme["panel_border"], (knob_cx, track.centery), knob_r + 2)
        pygame.draw.circle(surface, knob_color, (knob_cx, track.centery), knob_r)


class Toggle:
    """Labelled on/off switch rendered as a full row."""

    def __init__(self, rect, label, value, on_change):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = bool(value)
        self.on_change = on_change

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and getattr(event, "button", 0) == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.value = not self.value
            if self.on_change is not None:
                self.on_change(self.value)
            return True
        return False

    def draw(self, surface):
        theme = get_theme()
        rect = self.rect
        pad = max(6, rect.h // 4)
        draw_text(
            surface,
            self.label,
            rect.h * 0.42,
            theme["text"],
            (rect.x + pad, rect.centery),
            "midleft",
        )
        pill_w = int(rect.h * 1.5)
        pill_h = max(12, int(rect.h * 0.62))
        pill = pygame.Rect(rect.right - pad - pill_w, rect.centery - pill_h // 2, pill_w, pill_h)
        color = theme["accent_dark"] if self.value else theme["slider_track"]
        pygame.draw.rect(surface, color, pill, border_radius=pill_h // 2)
        knob_r = max(3, pill_h // 2 - 3)
        knob_cx = pill.right - pill_h // 2 if self.value else pill.x + pill_h // 2
        pygame.draw.circle(surface, theme["text"], (knob_cx, pill.centery), knob_r)


# Shown when a direction row is waiting and the user hits P once (Task 26):
# P is the pause key, so binding it needs an explicit second-press confirm.
P_PAUSE_WARNING = "P is used for pause - click row again to force"


class KeyBindRow:
    """Row that shows an action's key and rebinds it on click.

    Clicking enters 'press any key' mode; ESC cancels; any other key is
    reported through on_rebind(action, key_name) which handles conflict swaps.
    keyname may be None (unbound via the UnbindButton) -> "[ unbound ]".
    Pressing P while waiting arms the row instead of binding (Task 26): the
    inline P_PAUSE_WARNING replaces the label until the row is clicked again
    and P is pressed a second time (or another key / ESC / click-elsewhere
    resolves it).
    """

    def __init__(self, rect, action, keyname, on_rebind):
        self.rect = pygame.Rect(rect)
        self.action = action
        self.keyname = keyname
        self.on_rebind = on_rebind
        self.waiting = False
        self.armed = False  # P pressed once: next P force-binds
        self.warning = ""

    def _clear_warning(self):
        self.armed = False
        self.warning = ""

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            if self.rect.collidepoint(event.pos):
                self.waiting = True  # armed survives the re-click (force path)
                return True
            # Click elsewhere: cancel waiting + dismiss any lingering warning.
            self.waiting = False
            self._clear_warning()
        if self.waiting and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.waiting = False  # ESC stays reserved
                self._clear_warning()
            else:
                from game.constants import KEY_TO_NAME

                name = KEY_TO_NAME.get(event.key)
                if name is None:
                    name = "key%d" % event.key
                if name == "p" and not self.armed:
                    # First P: warn, do NOT bind. Click row again + press P
                    # to force; any other key binds and clears the warning.
                    self.armed = True
                    self.warning = P_PAUSE_WARNING
                    self.waiting = False
                else:
                    self.on_rebind(self.action, name)
                    self.waiting = False
                    self._clear_warning()
            return True
        if (
            self.armed
            and not self.waiting
            and event.type == pygame.KEYDOWN
            and event.key == pygame.K_ESCAPE
        ):
            self._clear_warning()  # ESC also dismisses a lingering P warning
            return True
        return False

    def prompt_text(self):
        """Text shown in the key box ("[ unbound ]" after an unbind)."""
        if self.waiting:
            return "press any key...  (esc to cancel)"
        if self.keyname is None:
            return "[ unbound ]"
        return key_label(self._keycode())

    def draw(self, surface):
        theme = get_theme()
        rect = self.rect
        radius = max(4, rect.h // 4)
        pad = max(6, rect.h // 4)
        pygame.draw.rect(surface, theme["panel"], rect, border_radius=radius)
        border = theme["warning"] if self.waiting else theme["neon_cyan"]
        pygame.draw.rect(surface, border, rect, width=3 if self.waiting else 2,
                         border_radius=radius)

        if self.armed and self.warning:
            # Inline P-conflict warning replaces the action label (Task 26).
            warn_size = rect.h * 0.32
            warn_font = get_font(warn_size)
            warn_text = fit_text(warn_font, self.warning, rect.w - 2 * pad - int(rect.w * 0.30))
            draw_text(
                surface,
                warn_text,
                warn_size,
                theme["warning"],
                (rect.x + pad, rect.centery),
                "midleft",
            )
        else:
            draw_text(
                surface,
                ACTION_LABELS[self.action],
                rect.h * 0.42,
                theme["text"],
                (rect.x + pad, rect.centery),
                "midleft",
            )

        prompt = self.prompt_text()
        font = get_font(rect.h * 0.4, bold=True)
        prompt = fit_text(font, prompt, rect.w - 2 * pad - int(rect.w * 0.45))
        try:
            image = font.render(prompt, True, theme["warning"] if self.waiting else theme["text"])
        except Exception:
            return
        box_w = image.get_width() + pad * 2
        box_h = max(12, rect.h - pad * 2)
        box = pygame.Rect(rect.right - pad - box_w, rect.centery - box_h // 2, box_w, box_h)
        pygame.draw.rect(surface, theme["button"], box, border_radius=max(3, box_h // 4))
        pygame.draw.rect(surface, border, box, width=1, border_radius=max(3, box_h // 4))
        surface.blit(image, image.get_rect(center=box.center))

    def _keycode(self):
        from game.constants import NAME_TO_KEY

        return NAME_TO_KEY.get(self.keyname, -1)


class UnbindButton:
    """Small square button with a code-drawn bin/trash icon (Task 22).

    Sits immediately right of a KeyBindRow; clicking it calls
    on_unbind(action) — the owning screen sets the binding to None and
    saves. The icon is drawn purely from rects/lines (lid + handle + body
    + vertical lines) so it renders without any font-glyph or emoji
    support. Follows the neon Button styling (hover glow, magenta press).
    """

    def __init__(self, rect, action, on_unbind):
        self.rect = pygame.Rect(rect)
        self.action = action
        self.on_unbind = on_unbind
        self.hovered = False
        self.pressed = False

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and getattr(event, "button", 0) == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.pressed = True
            self.on_unbind(self.action)
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False
        return False

    def _bin_rects(self):
        """Proportional sub-rects of the bin icon inside the button."""
        rect = self.rect
        w, h = rect.w, rect.h
        lid_w = max(6, int(w * 0.50))
        lid_h = max(2, int(h * 0.10))
        handle_w = max(3, int(w * 0.22))
        handle_h = max(2, int(h * 0.08))
        body_w = max(6, int(w * 0.38))
        body_top = rect.centery - int(h * 0.14)
        body_h = max(6, int(h * 0.44))
        lid = pygame.Rect(0, 0, lid_w, lid_h)
        lid.center = (rect.centerx, body_top - lid_h)
        handle = pygame.Rect(0, 0, handle_w, handle_h)
        handle.center = (rect.centerx, lid.centery - handle_h)
        body = pygame.Rect(0, 0, body_w, body_h)
        body.center = (rect.centerx, body_top + body_h // 2)
        return handle, lid, body

    def draw(self, surface):
        theme = get_theme()
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        hot = self.hovered or self.pressed
        border = theme["neon_magenta"] if self.pressed else theme["neon_cyan"]
        base = theme["button_hover"] if hot else theme["button"]
        radius = max(3, self.rect.h // 4)
        if hot:
            draw_glow_rect(surface, border, self.rect, radius, alpha=45, grow=4)
        pygame.draw.rect(surface, base, self.rect, border_radius=radius)
        pygame.draw.rect(surface, border, self.rect, width=3 if hot else 2,
                         border_radius=radius)

        icon = theme["neon_magenta"] if hot else theme["text"]
        handle, lid, body = self._bin_rects()
        line_w = max(1, self.rect.w // 16)
        try:
            pygame.draw.rect(surface, icon, handle, border_radius=1)
            pygame.draw.rect(surface, icon, lid, border_radius=1)
            pygame.draw.rect(surface, icon, body, width=max(1, line_w),
                             border_radius=max(1, line_w))
            # Two vertical lines inside the body (classic bin markings).
            stripe_x = max(2, body.w // 3)
            for dx in (-stripe_x // 2, stripe_x // 2):
                x = body.centerx + dx
                pygame.draw.line(
                    surface, icon,
                    (x, body.y + max(2, line_w)),
                    (x, body.bottom - max(2, line_w)),
                    1,
                )
        except (ValueError, TypeError):
            pass


class CycleRow:
    """Labelled row with < > arrows cycling through a value (track, display...).

    value_text is refreshed by the owning screen each frame; clicking an arrow
    fires on_prev / on_next. Long values are ellipsized to fit the box.
    """

    def __init__(self, rect, label, on_prev, on_next):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value_text = ""
        self.on_prev = on_prev
        self.on_next = on_next

    def _box(self):
        rect = self.rect
        pad = max(6, rect.h // 4)
        box_w = max(120, min(int(rect.w * 0.52), 320))
        box_h = max(16, rect.h - pad * 2)
        return pygame.Rect(rect.right - pad - box_w, rect.centery - box_h // 2, box_w, box_h)

    def _arrow_zones(self):
        box = self._box()
        arrow_w = max(16, box.h)
        prev = pygame.Rect(box.x, box.y, arrow_w, box.h)
        nxt = pygame.Rect(box.right - arrow_w, box.y, arrow_w, box.h)
        return prev, nxt

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            if not self.rect.collidepoint(event.pos):
                return False
            prev, nxt = self._arrow_zones()
            if prev.collidepoint(event.pos):
                if self.on_prev is not None:
                    self.on_prev()
                return True
            if nxt.collidepoint(event.pos):
                if self.on_next is not None:
                    self.on_next()
                return True
        return False

    def draw(self, surface):
        theme = get_theme()
        rect = self.rect
        pad = max(6, rect.h // 4)
        draw_text(
            surface,
            self.label,
            rect.h * 0.42,
            theme["text"],
            (rect.x + pad, rect.centery),
            "midleft",
        )
        box = self._box()
        radius = max(4, box.h // 4)
        pygame.draw.rect(surface, theme["button"], box, border_radius=radius)
        pygame.draw.rect(surface, theme["neon_cyan"], box, width=2, border_radius=radius)

        prev, nxt = self._arrow_zones()
        mouse = pygame.mouse.get_pos()
        for zone in (prev, nxt):
            if zone.collidepoint(mouse):
                pygame.draw.rect(surface, theme["button_hover"], zone, border_radius=radius)
        for zone, glyph in ((prev, "<"), (nxt, ">")):
            hovered = zone.collidepoint(mouse)
            draw_text(
                surface,
                glyph,
                box.h * 0.72,
                theme["neon_cyan"] if hovered else theme["text"],
                zone.center,
                "center",
                bold=True,
            )

        font = get_font(box.h * 0.55, bold=True)
        max_w = box.w - 2 * max(16, box.h) - 8
        value = fit_text(font, self.value_text, max_w)
        draw_text(surface, value, box.h * 0.55, theme["text"], box.center, "center")


class GlitchTitle:
    """Big neon heading with an occasional slice + RGB-fringe glitch (Task 26).

    Every ~1.5 s a random 120 ms glitch fires: magenta/cyan fringes blink
    behind the text and three horizontal slices pop to random x offsets.
    reduced_motion (accessibility) freezes it on the clean neon render.
    """

    INTERVAL_MS = 1500.0
    GLITCH_MS = 120.0

    def __init__(self, text, reduced_motion=False):
        self.text = str(text)
        self.reduced_motion = bool(reduced_motion)
        self.glitch_ms = 0.0
        self._until_glitch = self.INTERVAL_MS * (0.4 + random.random() * 0.6)
        self._image_cache = {}

    def update(self, dt):
        dt = float(dt)
        if self.reduced_motion:
            self.glitch_ms = 0.0
            return
        self.glitch_ms = max(0.0, self.glitch_ms - dt)
        self._until_glitch -= dt
        if self._until_glitch <= 0.0:
            self.glitch_ms = self.GLITCH_MS
            self._until_glitch = self.INTERVAL_MS * (0.6 + random.random() * 0.9)

    def _render(self, size, color):
        key = (int(round(size)), (int(color[0]), int(color[1]), int(color[2])))
        image = self._image_cache.get(key)
        if image is None:
            image = get_font(size, True).render(self.text, True, color)
            self._image_cache[key] = image
        return image

    def draw(self, surface, size, color, center):
        """Render the title centered on `center`; returns the text rect."""
        theme = get_theme()
        base = self._render(size, color)
        rect = base.get_rect(center=center)
        # Soft neon halo behind everything.
        try:
            halo = self._render(size, lerp_color(color, theme["bg"], 0.55))
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                surface.blit(halo, rect.move(dx, dy))
        except Exception:
            pass
        surface.blit(base, rect)
        if self.glitch_ms <= 0.0:
            return rect
        # Glitch beat: magenta/cyan fringe ghosts, then displaced slices.
        try:
            white = self._render(size, (255, 255, 255))
            fringe_m = white.copy()
            fringe_m.fill((*theme["neon_magenta"], 120),
                          special_flags=pygame.BLEND_RGBA_MULT)
            fringe_c = white.copy()
            fringe_c.fill((*theme["neon_cyan"], 120),
                          special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(fringe_m, rect.move(2, 0))
            surface.blit(fringe_c, rect.move(-2, 0))
        except Exception:
            pass
        w, h = base.get_size()
        for _ in range(3):
            band = max(4, h // 5)
            sy = random.randint(0, max(0, h - band))
            band = min(band, h - sy)
            if band <= 0:
                continue
            try:
                piece = base.subsurface(pygame.Rect(0, sy, w, band))
            except (ValueError, pygame.error):
                continue
            surface.blit(piece, (rect.x + random.randint(-8, 8), rect.y + sy))
        return rect
