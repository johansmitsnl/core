"""Support for Broadlink sensors."""
from __future__ import annotations

import logging
from typing import NamedTuple

import voluptuous as vol

from homeassistant.components.sensor import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.const import CONF_HOST, PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .entity import BroadlinkEntity
from .helpers import import_device

_LOGGER = logging.getLogger(__name__)


class SensorMetadata(NamedTuple):
    """Metadata for an individual sensor."""

    name: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None


SENSOR_TYPES: dict[str, SensorMetadata] = {
    "temperature": SensorMetadata(
        "Temperature",
        unit=TEMP_CELSIUS,
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    "air_quality": SensorMetadata(
        "Air Quality",
    ),
    "humidity": SensorMetadata(
        "Humidity",
        unit=PERCENTAGE,
        device_class=DEVICE_CLASS_HUMIDITY,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    "light": SensorMetadata(
        "Light",
        device_class=DEVICE_CLASS_ILLUMINANCE,
    ),
    "noise": SensorMetadata("Noise"),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_HOST): cv.string}, extra=vol.ALLOW_EXTRA
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import the device and discontinue platform.

    This is for backward compatibility.
    Do not use this method.
    """
    import_device(hass, config[CONF_HOST])
    _LOGGER.warning(
        "The sensor platform is deprecated, please remove it from your configuration"
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Broadlink sensor."""
    device = hass.data[DOMAIN].devices[config_entry.entry_id]
    sensor_data = device.update_manager.coordinator.data
    sensors = [
        BroadlinkSensor(device, monitored_condition)
        for monitored_condition in sensor_data
        if sensor_data[monitored_condition] != 0 or device.api.type == "A1"
    ]
    async_add_entities(sensors)


class BroadlinkSensor(BroadlinkEntity, SensorEntity):
    """Representation of a Broadlink sensor."""

    def __init__(self, device, monitored_condition):
        """Initialize the sensor."""
        super().__init__(device)
        self._coordinator = device.update_manager.coordinator
        self._monitored_condition = monitored_condition

        self._attr_device_class = SENSOR_TYPES[monitored_condition].device_class
        self._attr_name = f"{device.name} {SENSOR_TYPES[monitored_condition].name}"
        self._attr_state_class = SENSOR_TYPES[monitored_condition].state_class
        self._attr_state = self._coordinator.data[monitored_condition]
        self._attr_unique_id = f"{device.unique_id}-{monitored_condition}"
        self._attr_unit_of_measurement = SENSOR_TYPES[monitored_condition].unit

    @callback
    def update_data(self):
        """Update data."""
        if self._coordinator.last_update_success:
            self._attr_state = self._coordinator.data[self._monitored_condition]
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Call when the sensor is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self.update_data))

    async def async_update(self):
        """Update the sensor."""
        await self._coordinator.async_request_refresh()
