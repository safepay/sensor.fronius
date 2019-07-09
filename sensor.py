"""Support for the Fronius Inverter."""
import logging
from datetime import timedelta

import requests
import voluptuous as vol

import json

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, CONF_NAME, ATTR_ATTRIBUTION
    )
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_INVERTERRT = 'http://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=system&DeviceId=1&DataCollection=CommonInverterData'
_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Fronius Inverter Data"

CONF_NAME = 'name'
CONF_IP_ADDRESS = 'ip_address'
CONF_SCOPE = 'scope'
CONF_DEVICE_ID = 'device_id'
CONF_DATA_COLLECTION = 'data_collection'

SCOPE_TYPES = ['device', 'system']
DATA_COLLECTION_TYPES = ['CumulationInverterData', 'CommonInverterData', '3PInverterData', 'MinMaxInverterData']

DEFAULT_SCOPE = 'device'
DEFAULT_DEVICE_ID = '1'
DEFAULT_DATA_COLLECTION = 'CommonInverterData'

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

# Key: ['json_key', 'name', unit, icon]
SENSOR_TYPES = {
    'ac_power': ['PAC', 'AC Power', 'W', 'mdi:solar-power'],
    'ac_current': ['IAC', 'AC Current', 'A', 'mdi:solar-power'],
    'ac_voltage': ['UAC', 'AC Voltage', 'V', 'mdi:solar-power'],
    'ac_frequency': ['FAC', 'AC Frequency', 'Hz', 'mdi:solar-power'],
    'dc_current': ['IDC', 'DC Current', 'A', 'mdi:solar-power'],
    'dc_voltage': ['UDC', 'DC Voltage', 'V', 'mdi:solar-power'],
    'day_energy': ['DAY_ENERGY', 'Day Energy', 'kWh', 'mdi:solar-power'],
    'year_energy': ['YEAR_ENERGY', 'Year Energy', 'kWh', 'mdi:solar-power'],
    'total_energy': ['TOTAL_ENERGY', 'Total Energy', 'kWh', 'mdi:solar-power']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_SCOPE, default=DEFAULT_SCOPE):
        vol.In(SCOPE_TYPES),
    vol.Optional(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): cv.string,
    vol.Optional(CONF_NAME, default='Fronius'): cv.string,
    vol.Optional(CONF_DATA_COLLECTION, default=DEFAULT_DATA_COLLECTION):
        vol.In(DATA_COLLECTION_TYPES),
    vol.Required(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Fronius inverter sensor."""

    ip_address = config[CONF_IP_ADDRESS]
    scope = config.get(CONF_SCOPE)
    device_id = config.get(CONF_DEVICE_ID)
    data_collection = config.get(CONF_DATA_COLLECTION)
    name = config.get(CONF_NAME)

    fronius_data = FroniusData(ip_address, scope, device_id, data_collection)

    try:
        fronius_data.update()
    except ValueError as err:
        _LOGGER.error("Received error from inverter: %s", err)
        return

    dev = []
    for variable in config[CONF_MONITORED_CONDITIONS]:
        dev.append(FroniusSensor(fronius_data, name, variable, scope, device_id))

    add_entities(dev, True)


class FroniusSensor(Entity):
    """Implementation of the Fronius inverter sensor."""

    def __init__(self, inverter_data, name, sensor_type, scope, device_id):
        """Initialize the sensor."""
        self._client = name
        self._json_key = SENSOR_TYPES[sensor_type][0]
        self._name = SENSOR_TYPES[sensor_type][1]
        self._type = sensor_type
        self._state = None
        self._scope = scope
        self._device_id = device_id
        self._unit = SENSOR_TYPES[sensor_type][2]
        self._data = inverter_data
        self._icon = SENSOR_TYPES[sensor_type][3]

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._client, self._name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_ATTRIBUTION: ATTRIBUTION}
        return attrs

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    def update(self):
        """Get the latest data from inverter and update the states."""
        self._data.update()
        if not self._data:
            _LOGGER.info("Didn't receive data from the inverter")
            return

        _LOGGER.info("!!!!!!!!!!!!!!!!!!!!!!!!!! JSON KEY: %s", self._json_key)


        # Read data
        if self._unit == "kWh":
            self._state = round(self._data.latest_data[self._json_key]["Value"] / 1000, 1)
        else:
            self._state = round(self._data.latest_data[self._json_key]["Value"], 1)


class FroniusData:
    """Handle Fronius API object and limit updates."""

    def __init__(self, ip_address, scope, device_id, data_collection):
        """Initialize the data object."""
        self._ip_address = ip_address
        self._scope = scope
        self._device_id = device_id
        self._data_collection = data_collection

    def _build_url(self):
        """Build the URL for the requests."""
        url = _INVERTERRT.format(self._ip_address)
        _LOGGER.info("Fronius URL: %s", url)
        return url

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from inverter."""
        URLParams = [
            ("Scope", self._scope),
            ("DeviceId", self._device_id),
            ("DataCollection", self._data_collection)
        ]

        try:

            #result = requests.get("https://my-json-server.typicode.com/safepay/json/test", params=URLParams, timeout=10).json()
            result = requests.get(self._build_url(), timeout=10).json()
            #result = requests.get(self._build_url(), params=URLParams, timeout=10).json()

            _LOGGER.info("!!!!!!!!!!!!!!!!!!!!!!!!!! HEADER TIMESTAMP: %s", result['Head']['Timestamp'])


            self._data = result['Body']['Data']
            return
        except ValueError as err:
            _LOGGER.error("*** Error getting Fronius data")
