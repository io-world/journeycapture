from __future__ import annotations

from typing import Any, Literal

import httpx

from journeycapture_mcp.config import Settings


class JourneyCaptureError(RuntimeError):
    """Raised when the broker's HTTP API returns an error response."""


class JourneyCaptureClient:
    """Thin async wrapper around the broker's HTTP API — every method targets one
    machine_id, routed by the broker to that machine's websocket connection."""

    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(
            base_url=f"{settings.broker_scheme}://{settings.broker_host}:{settings.broker_port}",
            headers={"X-API-Key": settings.broker_api_key},
            timeout=settings.timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise JourneyCaptureError(f"{method} {path} failed: {e}") from e
        if resp.status_code >= 400:
            raise JourneyCaptureError(f"{method} {path} -> {resp.status_code}: {resp.text}")
        return resp

    async def list_machines(self) -> list[str]:
        resp = await self._request("GET", "/machines")
        return resp.json()

    async def health(self, machine: str) -> dict:
        resp = await self._request("GET", f"/machines/{machine}/health")
        return resp.json()

    async def list_monitors(self, machine: str) -> list[dict]:
        resp = await self._request("GET", f"/machines/{machine}/screenshot/monitors")
        return resp.json()

    async def screenshot(
        self,
        machine: str,
        format: Literal["png", "jpeg"] | None = None,
        quality: int | None = None,
        monitor: int | None = None,
    ) -> tuple[bytes, str]:
        params = {k: v for k, v in {"format": format, "quality": quality, "monitor": monitor}.items() if v is not None}
        resp = await self._request("GET", f"/machines/{machine}/screenshot", params=params)
        return resp.content, resp.headers.get("content-type", "image/jpeg")

    async def move_mouse(self, machine: str, x: int, y: int, relative: bool = False) -> dict:
        resp = await self._request(
            "POST", f"/machines/{machine}/mouse/move", json={"x": x, "y": y, "relative": relative}
        )
        return resp.json()

    async def click_mouse(
        self,
        machine: str,
        button: Literal["left", "right", "middle"] = "left",
        action: Literal["click", "down", "up"] = "click",
        clicks: int = 1,
        x: int | None = None,
        y: int | None = None,
    ) -> dict:
        body: dict[str, Any] = {"button": button, "action": action, "clicks": clicks}
        if x is not None:
            body["x"] = x
        if y is not None:
            body["y"] = y
        resp = await self._request("POST", f"/machines/{machine}/mouse/click", json=body)
        return resp.json()

    async def scroll_mouse(self, machine: str, dx: int = 0, dy: int = 0) -> dict:
        resp = await self._request("POST", f"/machines/{machine}/mouse/scroll", json={"dx": dx, "dy": dy})
        return resp.json()

    async def type_text(self, machine: str, text: str) -> dict:
        resp = await self._request("POST", f"/machines/{machine}/keyboard/type", json={"text": text})
        return resp.json()

    async def send_keys(
        self, machine: str, keys: list[str], action: Literal["press", "release", "tap"] = "tap"
    ) -> dict:
        resp = await self._request(
            "POST", f"/machines/{machine}/keyboard/key", json={"keys": keys, "action": action}
        )
        return resp.json()
