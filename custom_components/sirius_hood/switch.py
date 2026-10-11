"""Switch platform for Sirius Range Hood."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CAP_AUTO_MODE,
    CAP_BIPOWER,
    CAP_CLEAN_AIR,
    CAP_QUALITY_AIR,
    DOMAIN,
)
from .sirius_api import SiriusApiClient

_LOGGER = logging.getLogger(__name__)

SWITCH_TYPES = [
    {
        "key": "bipower",
        "name": "Smart-Switch Bi-Power",
        "cap": CAP_BIPOWER,
        "icon": "mdi:lightning-bolt",
    },
    {
        "key": "clean_air",
        "name": "Clean Air 24h",
        "cap": CAP_CLEAN_AIR,
        "icon": "mdi:air-filter",
    },
    {
        "key": "auto_mode",
        "name": "Auto Mode",
        "cap": CAP_AUTO_MODE,
        "icon": "mdi:auto-fix",
    },
    {
        "key": "quality_air",
        "name": "Air Quality Monitoring",
        "cap": CAP_QUALITY_AIR,
        "icon": "mdi:gauge",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sirius Range Hood switch platform."""
    client: SiriusApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for uid, dev_info in coordinator.data.items():
        caps = dev_info.get("caps", {})
        for s_def in SWITCH_TYPES:
            cap_id = s_def["cap"]
            if cap_id in caps:
                entities.append(
                    SiriusHoodSwitch(
                        coordinator,
                        client,
                        uid,
                        s_def["key"],
                        s_def["name"],
                        cap_id,
                        s_def["icon"],
                    )
                )

    async_add_entities(entities)


class SiriusHoodSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Sirius hood toggle switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: SiriusApiClient,
        device_uid: str,
        switch_key: str,
        name: str,
        cap_id: str,
        icon: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._device_uid = device_uid
        self._switch_key = switch_key
        self._cap_id = cap_id
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{device_uid}_{switch_key}"

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
        """Return true if switch is on."""
        return int(self._caps.get(self._cap_id, 0) or 0) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._client.set_capability(self._device_uid, self._cap_id, 1)
        self._caps[self._cap_id] = 1
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, self._cap_id, 1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._client.set_capability(self._device_uid, self._cap_id, 0)
        self._caps[self._cap_id] = 0
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, self._cap_id, 0)
        self.async_write_ha_state()
