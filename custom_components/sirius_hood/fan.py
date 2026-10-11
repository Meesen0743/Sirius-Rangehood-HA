"""Fan platform for Sirius Range Hood."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    CAP_BIPOWER,
    CAP_FAN_BOOST,
    CAP_FAN_FLOW,
    CAP_FAN_POWER,
    CAP_FAN_SPEED,
    DOMAIN,
)
from .sirius_api import SiriusApiClient

_LOGGER = logging.getLogger(__name__)

SPEED_RANGE = (1, 4)
PRESET_NORMAL = "Normal"
PRESET_BOOST = "Boost"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sirius Range Hood fan platform."""
    client: SiriusApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for uid, dev_info in coordinator.data.items():
        # Check if device has fan speed capability
        caps = dev_info.get("caps", {})
        if CAP_FAN_SPEED in caps or dev_info.get("model"):
            entities.append(SiriusHoodFan(coordinator, client, uid))

    async_add_entities(entities)


class SiriusHoodFan(CoordinatorEntity, FanEntity):
    """Representation of a Sirius Range Hood Fan."""

    _attr_has_entity_name = True
    _attr_name = "Fan"
    _attr_preset_modes = [PRESET_NORMAL, PRESET_BOOST]

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: SiriusApiClient,
        device_uid: str,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._client = client
        self._device_uid = device_uid
        self._attr_unique_id = f"{device_uid}_fan"

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
    def supported_features(self) -> FanEntityFeature:
        """Supported features."""
        return (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.PRESET_MODE
        )

    @property
    def speed_count(self) -> int:
        """Return the number of speeds."""
        return int_states_in_range(SPEED_RANGE)

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        speed = int(self._caps.get(CAP_FAN_SPEED, 0) or 0)
        return speed > 0

    @property
    def percentage(self) -> Optional[int]:
        """Return current speed as percentage."""
        speed = int(self._caps.get(CAP_FAN_SPEED, 0) or 0)
        if speed <= 0:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        speed = int(self._caps.get(CAP_FAN_SPEED, 0) or 0)
        if speed == 4:
            return PRESET_BOOST
        return PRESET_NORMAL

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if CAP_FAN_POWER in self._caps:
            attrs["power_w"] = self._caps[CAP_FAN_POWER]
        if CAP_FAN_FLOW in self._caps:
            attrs["flow_m3h"] = self._caps[CAP_FAN_FLOW]
        if CAP_BIPOWER in self._caps:
            attrs["bipower_enabled"] = bool(self._caps[CAP_BIPOWER])
        speed = int(self._caps.get(CAP_FAN_SPEED, 0) or 0)
        attrs["boost_active"] = (speed == 4)
        return attrs

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        speed = int(round(percentage_to_ranged_value(SPEED_RANGE, percentage)))
        await self._client.set_fan_speed(self._device_uid, speed)
        self._caps[CAP_FAN_SPEED] = speed
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, CAP_FAN_SPEED, speed)
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode == PRESET_BOOST:
            await self.async_set_preset_mode(PRESET_BOOST)
            return

        if percentage is not None:
            await self.async_set_percentage(percentage)
            return

        # Default to speed 1 if currently off
        current_speed = int(self._caps.get(CAP_FAN_SPEED, 0) or 0)
        target_speed = current_speed if current_speed > 0 else 1
        await self._client.set_fan_speed(self._device_uid, target_speed)
        self._caps[CAP_FAN_SPEED] = target_speed
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, CAP_FAN_SPEED, target_speed)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self._client.set_fan_speed(self._device_uid, 0)
        self._caps[CAP_FAN_SPEED] = 0
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, CAP_FAN_SPEED, 0)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        target_speed = 4 if preset_mode == PRESET_BOOST else 3
        await self._client.set_fan_speed(self._device_uid, target_speed)
        self._caps[CAP_FAN_SPEED] = target_speed
        if hasattr(self.coordinator, "set_optimistic_cap"):
            self.coordinator.set_optimistic_cap(self._device_uid, CAP_FAN_SPEED, target_speed)
        self.async_write_ha_state()
