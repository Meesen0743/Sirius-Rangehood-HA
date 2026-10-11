"""MQTT push client for live Sirius Range Hood state.

The REST ``/devices/`` endpoint returns a stale cloud shadow. The real,
live device state is published by the hood on the broker topic
``root/<tenant>/devices/<uid>/status`` - exactly like the official app.
"""
from __future__ import annotations

import json
import logging
import ssl
import uuid
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

from .const import MQTT_HOST, MQTT_PORT, MQTT_TENANT

_LOGGER = logging.getLogger(__name__)


class SiriusMqttClient:
    """Thread-based MQTT listener (paho runs its own network thread)."""

    def __init__(
        self,
        email: str,
        password: str,
        on_status: Callable[[str, Dict[str, Any]], None],
        device_uids: Optional[List[str]] = None,
    ) -> None:
        self._email = email
        self._password = password
        self._on_status = on_status
        self._device_uids: set[str] = set(device_uids or [])
        self._client: mqtt.Client | None = None

    def add_device(self, uid: str) -> None:
        """Add device UID to active subscription list."""
        if not uid or uid in self._device_uids:
            return
        self._device_uids.add(uid)
        if self._client:
            _LOGGER.debug("Sirius MQTT subscribing to new device: %s", uid)
            self._client.subscribe(f"root/{MQTT_TENANT}/devices/{uid}/status", 0)
            self._client.subscribe(f"root/{MQTT_TENANT}/devices/{uid}/response/#", 0)

    def start(self) -> None:
        """Connect and start the network loop (blocking setup, run in executor)."""
        client_id = f"ha-{uuid.uuid4().hex[:8]}"
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        except AttributeError:  # paho-mqtt 1.x
            client = mqtt.Client(client_id=client_id)

        client.username_pw_set(self._email, self._password)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        client.tls_set_context(ctx)
        client.on_connect = self._handle_connect
        client.on_message = self._handle_message
        client.reconnect_delay_set(min_delay=2, max_delay=60)
        self._client = client
        client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def _handle_connect(self, client, userdata, flags, rc, *args) -> None:
        _LOGGER.debug("Sirius MQTT connected (rc=%s)", rc)
        # Broker enforces ACLs strictly: wildcards '+' and '#' cause immediate kick/disconnect.
        # Subscribe specifically per device UID.
        for uid in self._device_uids:
            _LOGGER.debug("Sirius MQTT subscribing to device: %s", uid)
            client.subscribe(f"root/{MQTT_TENANT}/devices/{uid}/status", 0)
            client.subscribe(f"root/{MQTT_TENANT}/devices/{uid}/response/#", 0)

    def _handle_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return
        uid = data.get("deviceId")
        if not uid:
            parts = msg.topic.split("/")
            uid = parts[3] if len(parts) > 3 else None
        values = data.get("values")
        if not uid or not isinstance(values, list):
            return
        caps = {
            v["id"]: v.get("value")
            for v in values
            if isinstance(v, dict) and "id" in v
        }
        _LOGGER.debug("Sirius MQTT status for %s: %s", uid, caps)
        self._on_status(uid, caps)
