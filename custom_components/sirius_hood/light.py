"""Light platform for Sirius Range Hood."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CAP_LIGHT2_BRIGHTNESS,
    CAP_LIGHT2_COLORTEMP,
    CAP_LIGHT2_ONOFF,
    CAP_LIGHT2_POWER,
    CAP_LIGHT_BRIGHTNESS,
    CAP_LIGHT_COLORTEMP,
    CAP_LIGHT_ONOFF,
    CAP_LIGHT_POWER,
    DOMAIN,
)
from .sirius_api import SiriusApiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sirius Range Hood light platform."""
    client: SiriusApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for uid, dev_info in coordinator.data.items():
        caps = dev_info.get("caps", {})
        # Primary light
        if CAP_LIGHT_ONOFF in caps or dev_info.get("model"):
            entities.append(
                SiriusHoodLight(
                    coordinator,
                    client,
                    uid,
                    light_num=1,
                    on_cap=CAP_LIGHT_ONOFF,
                    bright_cap=CAP_LIGHT_BRIGHTNESS,
                    temp_cap=CAP_LIGHT_COLORTEMP,
                    power_cap=CAP_LIGHT_POWER,
                    name="Main Light",
                )
            )

        # Secondary / Ambient light (if supported by hood)
        if CAP_LIGHT2_ONOFF in caps:
            entities.append(
                SiriusHoodLight(
                    coordinator,
                    client,
                    uid,
                    light_num=2,
                    on_cap=CAP_LIGHT2_ONOFF,
                    bright_cap=CAP_LIGHT2_BRIGHTNESS,
                    temp_cap=CAP_LIGHT2_COLORTEMP,
                    power_cap=CAP_LIGHT2_POWER,
                    name="Ambient Light",
                )
            )

    async_add_entities(entities)


class SiriusHoodLight(CoordinatorEntity, LightEntity):
    """Representation of a Sirius Range Hood Light."""

    _attr_has_entity_name = True
    _attr_min_color_temp_kelvin = 2700
    _attr_max_color_temp_kelvin = 6500

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: SiriusApiClient,
        device_uid: str,
        light_num: int,
        on_cap: str,
        bright_cap: str,
        temp_cap: str,
        power_cap: str,
        name: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._client = client
        self._device_uid = device_uid
        self._light_num = light_num
        self._on_cap = on_cap
        self._bright_cap = bright_cap
        self._temp_cap = temp_cap
        self._power_cap = power_cap
        self._attr_name = name
        self._attr_unique_id = f"{device_uid}_light_{light_num}"

        # Color modes
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
        self._attr_color_mode = ColorMode.COLOR_TEMP

    @property
    def _dev_data(self) -> Dict[str, Any]:
        return self.coordinator.data.get(self._device_uid, {})

    @property
    def _caps(self) -> Dict[str, Any]:
        return self._dev_data.get("caps", {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_uid)},
            name=self._dev_data.get("name", "Sirius Hood"),
            manufacturer="Sirius",
            model=self._dev_data.get("model", "Smart-Switch Range Hood"),
            sw_version=self._dev_data.get("sw_version"),
        )

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return int(self._caps.get(self._on_cap, 0) or 0) == 1

    @property
    def brightness(self) -> Optional[int]:
        """Return current brightness (0-255)."""
        val_pct = self._caps.get(self._bright_cap)
        if val_pct is not None:
            return int(round((int(val_pct) / 100.0) * 255.0))
        return 255 if self.is_on else 0

    @property
    def color_temp_kelvin(self) -> Optional[int]:
        """Return color temperature in Kelvin."""
        kelvin = self._caps.get(self._temp_cap)
        if kelvin is not None and int(kelvin) > 0:
            return int(kelvin)
        return 4000

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if self._power_cap in self._caps:
            attrs["power_w"] = self._caps[self._power_cap]
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_BRIGHTNESS in kwargs:
            bright_255 = kwargs[ATTR_BRIGHTNESS]
            bright_pct = max(1, min(100, int(round((bright_255 / 255.0) * 100.0))))
            await self._client.set_capability(self._device_uid, self._bright_cap, bright_pct)
            self._caps[self._bright_cap] = bright_pct
            if hasattr(self.coordinator, "set_optimistic_cap"):
                self.coordinator.set_optimistic_cap(self._device_uid, self._bright_cap, bright_pct)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.set_capability(self._device_uid, self._temp_cap, kelvin)
            self._caps[self._temp_cap] = kelvin
            if hasattr(self.coordinator, "set_optimistic_cap"):
                self.coordinator.set_optimistic_cap(self._device_uid, self._temp_cap, kelvin)

        await self._client.set_capability(self._device_uid, self._on_cap, 1)
        self._caps[self._on_cap] = 1
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, self._on_cap, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._client.set_capability(self._device_uid, self._on_cap, 0)
        self._caps[self._on_cap] = 0
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, self._on_cap, 0)
        self.async_write_ha_state()
