"""The Sirius Range Hood integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .sirius_api import SiriusApiClient, SiriusApiError, SiriusAuthError
from .sirius_mqtt import SiriusMqttClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sirius Range Hood from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = async_get_clientsession(hass)
    client = SiriusApiClient(email=email, password=password, session=session)

    try:
        await client.login()
    except SiriusAuthError as err:
        _LOGGER.error("Failed to authenticate with Sirius Cloud: %s", err)
        return False
    except SiriusApiError as err:
        _LOGGER.warning("Could not reach Sirius Cloud during setup: %s", err)

    # Live state received over MQTT. The REST shadow is stale, so these
    # values always take precedence over what the poll returns.
    live_state: Dict[str, Dict[str, Any]] = {}

    async def async_update_data() -> Dict[str, Dict[str, Any]]:
        """Fetch device states from Sirius Cloud."""
        try:
            raw_devices = await client.get_devices()
            devices_map: Dict[str, Dict[str, Any]] = {}

            for dev in raw_devices:
                uid = dev.get("uid") or dev.get("id") or dev.get("mac")
                if not uid:
                    continue

                # Parse capabilities list into key-value map
                caps_map: Dict[str, Any] = {}
                capabilities = dev.get("capabilities", [])
                if isinstance(capabilities, list):
                    for cap in capabilities:
                        if isinstance(cap, dict):
                            cap_id = cap.get("capabilityUid") or cap.get("id")
                            if cap_id:
                                caps_map[cap_id] = cap.get("value")
                elif isinstance(capabilities, dict):
                    caps_map = capabilities

                device_name = dev.get("name") or dev.get("description") or "Sirius Range Hood"
                fw_version = dev.get("firmwareVersion") or dev.get("swVersion")

                # Also copy any properties
                properties = dev.get("properties", [])
                if isinstance(properties, list):
                    for prop in properties:
                        if isinstance(prop, dict):
                            p_id = prop.get("id")
                            p_val = prop.get("value")
                            if p_id:
                                caps_map[p_id] = p_val
                            if p_id == "property.device_name" and p_val:
                                device_name = p_val
                            elif p_id == "property.device.fw.version" and p_val:
                                fw_version = f"v{p_val}"

                caps_map.update(live_state.get(str(uid), {}))

                devices_map[str(uid)] = {
                    "raw": dev,
                    "caps": caps_map,
                    "name": device_name,
                    "model": dev.get("description") or "Smart-Switch Range Hood",
                    "sw_version": fw_version,
                }

            return devices_map
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Sirius Cloud: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"sirius_hood_{email}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    def _handle_mqtt_status(uid: str, caps: Dict[str, Any]) -> None:
        """Called from the paho thread; hop onto the HA loop."""

        def _apply() -> None:
            live_state.setdefault(uid, {}).update(caps)
            data = coordinator.data
            if not data or uid not in data:
                return
            new_data = dict(data)
            dev = dict(new_data[uid])
            merged = dict(dev.get("caps", {}))
            merged.update(caps)
            dev["caps"] = merged
            new_data[uid] = dev
            coordinator.async_set_updated_data(new_data)

        hass.loop.call_soon_threadsafe(_apply)

    mqtt_client = SiriusMqttClient(email, password, _handle_mqtt_status)
    await hass.async_add_executor_job(mqtt_client.start)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "mqtt": mqtt_client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(data["mqtt"].stop)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
