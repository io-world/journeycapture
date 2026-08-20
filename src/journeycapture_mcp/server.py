from __future__ import annotations

import logging
from typing import Literal

from mcp.server.mcpserver import Image, MCPServer

from journeycapture_mcp.client import JourneyCaptureClient

logger = logging.getLogger(__name__)


def build_server(client: JourneyCaptureClient) -> MCPServer:
    server = MCPServer(
        name="journeycapture",
        instructions="Remote-control a Windows desktop: move/click/scroll the mouse, type text or send key "
        "chords, and capture screenshots. Call health_check first if unsure the target machine is reachable.",
    )

    async def _resolve_xy(
        x: int | None,
        y: int | None,
        fx: float | None,
        fy: float | None,
        monitor: int | None,
        *,
        allow_neither: bool = False,
    ) -> tuple[int | None, int | None]:
        if (x is None) != (y is None):
            raise ValueError("x and y must be given together.")
        if (fx is None) != (fy is None):
            raise ValueError("fx and fy must be given together.")
        have_xy = x is not None
        have_fxy = fx is not None
        if have_xy and have_fxy:
            raise ValueError("Provide either x/y or fx/fy, not both.")
        if not have_xy and not have_fxy:
            if allow_neither:
                return None, None
            raise ValueError("Provide either x/y (pixel coordinates) or fx/fy (fraction of the screen, 0.0-1.0).")
        if have_xy:
            return x, y
        monitors = await client.list_monitors()
        index = monitor if monitor is not None else (1 if len(monitors) > 1 else 0)
        try:
            target = monitors[index]
        except IndexError:
            raise ValueError(f"monitor index {index} out of range (0..{len(monitors) - 1})") from None
        return target["left"] + round(fx * target["width"]), target["top"] + round(fy * target["height"])

    @server.tool()
    async def health_check() -> dict:
        """Check whether the journeycapture instance is reachable and report its version."""
        return await client.health()

    @server.tool()
    async def list_monitors() -> list[dict]:
        """List monitors with pixel bounds in the same coordinate space move_mouse uses. Index 0 is the bounding box of all monitors combined; physical monitors start at index 1. Always read the actual width/height from here (or from a screenshot's real pixel dimensions) before computing click/move coordinates — never assume a resolution like 1366x768. Guessing wrong is why a click can silently land on empty desktop instead of the intended icon."""
        logger.info("list_monitors")
        return await client.list_monitors()

    @server.tool()
    async def take_screenshot(
        format: Literal["png", "jpeg"] | None = None,
        quality: int | None = None,
        monitor: int | None = None,
    ) -> Image:
        """Capture a screenshot of one monitor. format/quality default to the server's own config when omitted; monitor index comes from list_monitors. Measure coordinates against this image's actual pixel dimensions (or list_monitors) — don't assume a resolution."""
        logger.info("take_screenshot format=%s quality=%s monitor=%s", format, quality, monitor)
        data, content_type = await client.screenshot(format=format, quality=quality, monitor=monitor)
        image_format = "png" if "png" in content_type else "jpeg"
        return Image(data=data, format=image_format)

    @server.tool()
    async def move_mouse(
        x: int | None = None,
        y: int | None = None,
        fx: float | None = None,
        fy: float | None = None,
        monitor: int | None = None,
        relative: bool = False,
    ) -> dict:
        """Move the cursor to an absolute screen position (x/y in pixels, or fx/fy as a fraction 0.0-1.0 of the target monitor's width/height), or by a relative offset (x/y only). (0, 0) is the primary monitor's top-left corner; monitors above/left of it have negative coordinates. Prefer fx/fy over x/y when targeting something visually identified from a screenshot — it's correct regardless of what resolution the image was actually perceived at, unlike guessing a pixel number against an assumed resolution. monitor selects which monitor fx/fy is relative to (default: the primary physical monitor, same as list_monitors index 1); fx/fy can't be combined with relative=True. Returns the resulting position — check it against what was requested."""
        if relative:
            if fx is not None or fy is not None:
                raise ValueError(
                    "fx/fy can't be combined with relative=True — a fraction of the screen isn't meaningful as a relative offset."
                )
            if x is None or y is None:
                raise ValueError("x and y are required when relative=True.")
            resolved_x, resolved_y = x, y
        else:
            resolved_x, resolved_y = await _resolve_xy(x, y, fx, fy, monitor)
        logger.info(
            "move_mouse x=%s y=%s fx=%s fy=%s monitor=%s relative=%s -> resolved (%s, %s)",
            x, y, fx, fy, monitor, relative, resolved_x, resolved_y,
        )
        return await client.move_mouse(resolved_x, resolved_y, relative=relative)

    @server.tool()
    async def click_mouse(
        button: Literal["left", "right", "middle"] = "left",
        action: Literal["click", "down", "up"] = "click",
        clicks: int = 1,
        x: int | None = None,
        y: int | None = None,
        fx: float | None = None,
        fy: float | None = None,
        monitor: int | None = None,
    ) -> dict:
        """Click a mouse button, optionally moving to x/y (pixels) or fx/fy (fraction 0.0-1.0 of the target monitor's width/height) first — omit all four to click at the current cursor position. Prefer fx/fy over x/y when targeting something visually identified from a screenshot — it's correct regardless of what resolution the image was actually perceived at. monitor selects which monitor fx/fy is relative to (default: the primary physical monitor, same as list_monitors index 1). Use action=down/up (instead of the default click) to hold a button across separate calls, e.g. for a drag — an unmatched down auto-releases after ~10s on the server."""
        resolved_x, resolved_y = await _resolve_xy(x, y, fx, fy, monitor, allow_neither=True)
        logger.info(
            "click_mouse button=%s action=%s clicks=%d x=%s y=%s fx=%s fy=%s monitor=%s -> resolved x=%s y=%s",
            button, action, clicks, x, y, fx, fy, monitor, resolved_x, resolved_y,
        )
        return await client.click_mouse(button=button, action=action, clicks=clicks, x=resolved_x, y=resolved_y)

    @server.tool()
    async def scroll_mouse(dx: int = 0, dy: int = 0) -> dict:
        """Scroll the mouse wheel at the current cursor position, in wheel notches (not pixels). Positive dy scrolls up, negative scrolls down; positive dx scrolls right, negative scrolls left."""
        logger.info("scroll_mouse dx=%d dy=%d", dx, dy)
        return await client.scroll_mouse(dx=dx, dy=dy)

    @server.tool()
    async def type_text(text: str) -> dict:
        """Type printable text into whatever window has focus. For non-printable keys (Enter, Tab, Ctrl+C, etc.) use send_keys instead — this only sends character keystrokes."""
        # Log the length only, never the text itself — it could be a password or
        # anything else sensitive typed into a remote window.
        logger.info("type_text %d character(s)", len(text))
        return await client.type_text(text)

    @server.tool()
    async def send_keys(keys: list[str], action: Literal["press", "release", "tap"] = "tap") -> dict:
        """Send one or more named keys, e.g. special keys or chords like ["ctrl", "c"] that type_text can't express. Each key is either a single printable character or a pynput.keyboard.Key name (enter, tab, esc, backspace, space, shift, ctrl, alt, cmd, up, down, left, right, f1-f20, etc). action="tap" (default) presses then releases; "press"/"release" hold or let go without the other half — an unmatched press auto-releases after ~10s on the server."""
        logger.info("send_keys keys=%s action=%s", keys, action)
        return await client.send_keys(keys, action=action)

    return server
