"""Sensor platform for Sirius Range Hood."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    CAP_CO2,
    CAP_FAN_FLOW,
    CAP_FAN_POWER,
    CAP_FILTER1_VALUE,
    CAP_FILTER2_VALUE,
    CAP_HUM,
    CAP_IAQ,
    CAP_LIGHT_POWER,
    CAP_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = [
    {
        "key": "fan_power",
        "name": "Fan Power",
        "cap": CAP_FAN_POWER,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:lightning-bolt",
    },
    {
        "key": "light_power",
        "name": "Light Power",
        "cap": CAP_LIGHT_POWER,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.WATT,
        "icon": "mdi:lightning-bolt",
    },
    {
        "key": "fan_flow",
        "name": "Air Flow",
        "cap": CAP_FAN_FLOW,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "m³/h",
        "icon": "mdi:weather-windy",
    },
    {
        "key": "co2",
        "name": "CO2",
        "cap": CAP_CO2,
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": CONCENTRATION_PARTS_PER_MILLION,
        "icon": "mdi:molecule-co2",
    },
    {
        "key": "iaq",
        "name": "Air Quality Index (IAQ)",
        "cap": CAP_IAQ,
        "device_class": SensorDeviceClass.AQI,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": None,
        "icon": "mdi:air-filter",
    },
    {
        "key": "temperature",
        "name": "Temperature",
        "cap": CAP_TEMP,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
    },
    {
        "key": "humidity",
        "name": "Humidity",
        "cap": CAP_HUM,
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:water-percent",
    },
    {
        "key": "filter1_life",
        "name": "Main Filter Life",
        "cap": CAP_FILTER1_VALUE,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:air-filter",
    },
    {
        "key": "filter2_life",
        "name": "Secondary Filter Life",
        "cap": CAP_FILTER2_VALUE,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:air-filter",
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sirius Range Hood sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for uid, dev_info in coordinator.data.items():
        caps = dev_info.get("caps", {})
        for s_def in SENSOR_DEFINITIONS:
            cap_id = s_def["cap"]
            if cap_id in caps:
                entities.append(
                    SiriusHoodSensor(
                        coordinator,
                        uid,
                        s_def["key"],
                        s_def["name"],
                        cap_id,
                        s_def.get("device_class"),
                        s_def.get("state_class"),
                        s_def.get("unit"),
                        s_def.get("icon"),
                    )
                )

    async_add_entities(entities)


class SiriusHoodSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sirius hood sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_uid: str,
        sensor_key: str,
        name: str,
        cap_id: str,
        device_class: Optional[SensorDeviceClass],
        state_class: Optional[SensorStateClass],
        unit: Optional[str],
        icon: Optional[str],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_uid = device_uid
        self._sensor_key = sensor_key
        self._cap_id = cap_id
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        if icon:
            self._attr_icon = icon
        self._attr_unique_id = f"{device_uid}_{sensor_key}"

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
    def native_value(self) -> Any:
        """Return the current sensor value."""
        val = self._caps.get(self._cap_id)
        if val is None:
            return None
        try:
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                if "." in val:
                    return float(val)
                return int(val)
        except (ValueError, TypeError):
            pass
        return val
