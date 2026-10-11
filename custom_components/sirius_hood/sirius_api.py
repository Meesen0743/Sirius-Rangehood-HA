"""Python Client for Sirius Range Hood Cloud API (PGA IoT)."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class SiriusAuthError(Exception):
    """Exception raised when authentication fails."""


class SiriusApiError(Exception):
    """Exception raised on general API errors."""


class SiriusApiClient:
    """Async API Client for Sirius Range Hoods."""

    def __init__(
        self,
        email: str,
        password: str,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.email = email
        self.password = password
        self._session = session
        self._owns_session = False
        self.jwt: Optional[str] = None
        self.token_expiry: float = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        """Close underlying session if owned."""
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def login(self) -> str:
        """Authenticate with Sirius Cloud and obtain JWT."""
        session = await self._get_session()
        url = f"{API_BASE_URL}/users/login"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "okhttp/4.9.1",
            "Accept": "application/json",
        }
        payload = {
            "email": self.email,
            "password": self.password,
        }

        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 401:
                    text = await response.text()
                    try:
                        data = json.loads(text) if text.strip() else {}
                        msg = data.get("message", "Unauthorized") if isinstance(data, dict) else "Unauthorized"
                    except Exception:
                        msg = "Unauthorized"
                    raise SiriusAuthError(f"Login failed (HTTP 401): {msg}")
                response.raise_for_status()
                text = await response.text()
                data = json.loads(text) if text.strip() else {}
                self.jwt = data.get("JWT") or data.get("jwt")
                expires_in = data.get("expires", 3600)
                self.token_expiry = time.time() + float(expires_in) - 60
                _LOGGER.debug("Sirius login successful. Token expires in %ds", expires_in)
                return self.jwt
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                raise SiriusAuthError("Invalid username or password.") from err
            raise SiriusApiError(f"HTTP error during login: {err}") from err
        except aiohttp.ClientError as err:
            raise SiriusApiError(f"Connection error during login: {err}") from err

    async def _ensure_auth(self) -> None:
        if not self.jwt or time.time() >= self.token_expiry:
            await self.login()

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Any:
        response.raise_for_status()
        text = await response.text()
        if not text.strip():
            return {}
        try:
            return json.loads(text)
        except Exception:
            return text

    async def request(self, method: str, path: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
        """Send authenticated request to Sirius Cloud."""
        await self._ensure_auth()
        session = await self._get_session()
        url = f"{API_BASE_URL}{path}"
        headers = {
            "User-Agent": "okhttp/4.9.1",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.jwt}",
        }
        if json_data is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with session.request(method, url, json=json_data, headers=headers) as response:
                if response.status == 401:
                    _LOGGER.info("Token expired during request, re-authenticating...")
                    await self.login()
                    headers["Authorization"] = f"Bearer {self.jwt}"
                    async with session.request(method, url, json=json_data, headers=headers) as retry_res:
                        return await self._parse_response(retry_res)
                return await self._parse_response(response)
        except aiohttp.ClientError as err:
            raise SiriusApiError(f"API request failed [{method} {path}]: {err}") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Fetch list of all devices associated with the account."""
        data = await self.request("GET", "/devices/")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Sometimes wrapped in {"_embedded": {"devices": [...]}} or {"devices": [...]}
            if "_embedded" in data and "devices" in data["_embedded"]:
                return data["_embedded"]["devices"]
            if "devices" in data:
                return data["devices"]
        return [data] if data else []

    async def set_capability(
        self,
        device_uid: str,
        capability_id: str,
        value: Any,
        device_type: str = "smartphone",
    ) -> Dict[str, Any]:
        """Send a capability value modification command to the hood."""
        payload = {
            "command": "setValue",
            "requestId": str(uuid.uuid4()),
            "parameters": [
                {
                    "id": capability_id,
                    "value": value,
                }
            ],
            "deviceType": device_type,
        }
        _LOGGER.debug(
            "Sending command to device %s: %s = %s",
            device_uid,
            capability_id,
            value,
        )
        return await self.request("POST", f"/devices/{device_uid}/set_value", json_data=payload)

    # Helper methods for standard controls
    async def set_fan_speed(self, device_uid: str, speed: int) -> None:
        """Set fan speed (0=Off, 1, 2, 3)."""
        await self.set_capability(device_uid, "device.fanSpeed", speed)

    async def set_fan_boost(self, device_uid: str, boost: bool) -> None:
        """Set fan boost mode."""
        await self.set_capability(device_uid, "device.boostValue", 1 if boost else 0)

    async def set_bipower(self, device_uid: str, enabled: bool) -> None:
        """Toggle Smart-Switch Bi-Power ECO / High Power mode."""
        await self.set_capability(device_uid, "device.biPowerEnabled", 1 if enabled else 0)

    async def set_light(self, device_uid: str, on: bool) -> None:
        """Toggle primary hood light."""
        await self.set_capability(device_uid, "device.lightOnOff", 1 if on else 0)

    async def set_light_brightness(self, device_uid: str, brightness_pct: int) -> None:
        """Set primary hood light brightness (0-100%)."""
        await self.set_capability(device_uid, "device.lightBrightness", max(0, min(100, brightness_pct)))

    async def set_light_color_temp(self, device_uid: str, kelvin: int) -> None:
        """Set primary hood light color temperature in Kelvin."""
        await self.set_capability(device_uid, "device.lightColorTemperature", kelvin)

    async def set_clean_air(self, device_uid: str, enabled: bool) -> None:
        """Toggle 24h Clean Air purification cycle."""
        await self.set_capability(device_uid, "device.cleanAirEnabled", 1 if enabled else 0)

    async def set_auto_mode(self, device_uid: str, enabled: bool) -> None:
        """Toggle automatic sensor-driven mode."""
        await self.set_capability(device_uid, "device.autoModeEnabled", 1 if enabled else 0)
