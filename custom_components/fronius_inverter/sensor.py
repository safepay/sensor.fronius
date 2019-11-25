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

_INVERTERRT = 'http://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope={}&DeviceId={}&DataCollection=CommonInverterData'
_POWERFLOW_URL = 'http://{}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
#_INVERTERRT = 'http://{}{}?DeviceId={}&DataCollection=CommonInverterData'
#_POWERFLOW_URL = 'http://{}PowerFlow'
_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Fronius Inverter Data"

CONF_NAME = 'name'
CONF_IP_ADDRESS = 'ip_address'
CONF_DEVICE_ID = 'device_id'
CONF_SCOPE = 'scope'
CONF_UNITS = 'units'
CONF_POWER_UNITS = 'power_units'
CONF_POWERFLOW = 'powerflow'

SCOPE_TYPES = ['Device', 'System']
UNIT_TYPES = ['Wh', 'kWh', 'MWh']
POWER_UNIT_TYPES = ['W', 'kW', 'MW']

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

# Key: ['device', 'system', 'json_key', 'name', 'unit', 'convert_units', 'icon']
SENSOR_TYPES = {
    'year_energy': ['inverter', True, 'YEAR_ENERGY', 'Year Energy', 'MWh', 'energy', 'mdi:solar-power'],
    'total_energy': ['inverter', True, 'TOTAL_ENERGY', 'Total Energy', 'MWh', 'energy', 'mdi:solar-power'],
    'ac_power': ['inverter', True, 'PAC', 'AC Power', 'W', 'power', 'mdi:solar-power'],
    'day_energy': ['inverter', True, 'DAY_ENERGY', 'Day Energy', 'kWh', False, 'mdi:solar-power'],
    'ac_current': ['inverter', False, 'IAC', 'AC Current', 'A', False, 'mdi:solar-power'],
    'ac_voltage': ['inverter', False, 'UAC', 'AC Voltage', 'V', False, 'mdi:solar-power'],
    'ac_frequency': ['inverter', False, 'FAC', 'AC Frequency', 'Hz', False, 'mdi:solar-power'],
    'dc_current': ['inverter', False, 'IDC', 'DC Current', 'A', False, 'mdi:solar-power'],
    'dc_voltage': ['inverter', False, 'UDC', 'DC Voltage', 'V', False, 'mdi:solar-power'],
    'grid_usage': ['powerflow', False, 'P_Grid', 'Grid Usage', 'W', 'power', 'mdi:solar-power'],
    'house_load': ['powerflow', False, 'P_Load', 'House Load', 'W', 'power', 'mdi:solar-power'],
    'panel_status': ['powerflow', False, 'P_PV', 'Panel Status', 'W', 'power', 'mdi:solar-panel']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_DEVICE_ID, default='1'): cv.string,
    vol.Optional(CONF_NAME, default='Fronius'): cv.string,
    vol.Optional(CONF_SCOPE, default='Device'):
        vol.In(SCOPE_TYPES),
    vol.Optional(CONF_UNITS, default='MWh'):
        vol.In(UNIT_TYPES),
    vol.Optional(CONF_POWER_UNITS, default='W'):
        vol.In(POWER_UNIT_TYPES),
    vol.Optional(CONF_POWERFLOW, default=False): cv.boolean,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Fronius inverter sensor."""

    ip_address = config[CONF_IP_ADDRESS]
    device_id = config.get(CONF_DEVICE_ID)
    scope = config.get(CONF_SCOPE)
    units = config.get(CONF_UNITS)
    power_units = config.get(CONF_POWER_UNITS)
    name = config.get(CONF_NAME)
    powerflow = config.get(CONF_POWERFLOW)

    inverter_data = InverterData(ip_address, device_id, scope)

    try:
        await inverter_data.async_update()
    except ValueError as err:
        _LOGGER.error("Received data error from Fronius inverter: %s", err)
        return

    if powerflow:
        powerflow_data = PowerflowData(ip_address)
        try:
            await powerflow_data.async_update()
        except ValueError as err:
            _LOGGER.error("Received data error from Fronius Powerflow: %s", err)
            return



    dev = []
    for variable in config[CONF_MONITORED_CONDITIONS]:

        device = SENSOR_TYPES[variable][0]
        system = SENSOR_TYPES[variable][1]
        convert_units = SENSOR_TYPES[variable][5]

        if convert_units == 'power':
            units = power_units

        sensor = "sensor." + name + "_" + SENSOR_TYPES[variable][3]
        state = hass.states.get(sensor)
    
        if device == "inverter":
            if scope == 'System' and system:
                dev.append(FroniusSensor(inverter_data, name, variable, scope, units, device_id, powerflow))
            elif  scope == 'Device':
                dev.append(FroniusSensor(inverter_data, name, variable, scope, units, device_id, powerflow))
        elif device == "powerflow" and powerflow:
            dev.append(FroniusSensor(powerflow_data, name, variable, scope, units, device_id, powerflow))

    async_add_entities(dev, True)

class FroniusSensor(Entity):
    """Implementation of the Fronius inverter sensor."""

    def __init__(self, device_data, name, sensor_type, scope, units, device_id, powerflow):
        """Initialize the sensor."""
        self._client = name
        self._device = SENSOR_TYPES[sensor_type][0]
        self._json_key = SENSOR_TYPES[sensor_type][2]
        self._name = SENSOR_TYPES[sensor_type][3]
        self._type = sensor_type
        self._state = None
        self._device_id = device_id
        self._scope = scope
        self._units = units
        self._unit = SENSOR_TYPES[sensor_type][4]
        self._convert_units = SENSOR_TYPES[sensor_type][5]
        self._data = device_data
        self._icon = SENSOR_TYPES[sensor_type][6]
        self._powerflow = powerflow

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
        if self._convert_units:
            return self._units
        else:
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

    async def async_update(self, utcnow=None):
        """Get the latest data from inverter and update the states."""

        # Prevent errors when data not present at night but retain long term states
        await self._data.async_update()
        if not self._data:
            _LOGGER.error("Didn't receive data from the inverter")
            return

        state = None
        if self._data.latest_data and (self._json_key in self._data.latest_data):
            _LOGGER.debug("Device: {}".format(self._device))
            if self._device == 'inverter':
                if self._scope == 'Device':
                    # Read data
                    state = self._data.latest_data[self._json_key]['Value']
                elif self._scope == 'System':
                    for item in self._data.latest_data[self._json_key]['Values']:
                        state = state + self._data.latest_data[self._json_key]['Values'][item]
            elif self._device == 'powerflow':
                # Read data
                if self._data.latest_data[self._json_key]:
                    state = self._data.latest_data[self._json_key]
            _LOGGER.debug("State: {}".format(state))

        # convert and round the result
        if state is not None:
            if self._convert_units == "energy":
                if self._units == "MWh":
                    self._state = round(state / 1000000, 2)
                elif self._units == "kWh":
                    self._state = round(state / 1000, 2)
                else:
                    self._state = round(state, 2)
            if self._convert_units == "power":
                if self._units == "MW":
                    self._state = round(state / 1000000, 2)
                elif self._units == "kW":
                    self._state = round(state / 1000, 2)
                else:
                    self._state = round(state, 2)
            elif self._json_key == "DAY_ENERGY":
                self._state = round(state / 1000, 2)
            else:
                self._state = round(state, 2)

class InverterData:
    """Handle Fronius API object and limit updates."""

    def __init__(self, ip_address, device_id, scope):
        """Initialize the data object."""
        self._ip_address = ip_address
        self._device_id = device_id
        self._scope = scope

    def _build_url(self):
        """Build the URL for the requests."""
        url = _INVERTERRT.format(self._ip_address, self._scope, self._device_id)
        _LOGGER.debug("Fronius Inverter URL: %s", url)
        return url

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the latest data from inverter."""
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to Fronius: %s", error)
            self._data = None

class PowerflowData:
    """Handle Fronius API object and limit updates."""

    def __init__(self, ip_address):
        """Initialize the data object."""
        self._ip_address = ip_address

    def _build_url(self):
        """Build the URL for the requests."""
        url = _POWERFLOW_URL.format(self._ip_address)
        _LOGGER.debug("Fronius Powerflow URL: %s", url)
        return url

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the latest data from inverter."""
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']['Site']
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to Powerflow: %s", error)
            self._data = None
