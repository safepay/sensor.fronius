"""Support for the Fronius Inverter."""
import logging
from datetime import timedelta

import requests
import voluptuous as vol
from requests.exceptions import (
    ConnectionError as ConnectError, HTTPError, Timeout)
import json
from numbers import Number

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, CONF_NAME, ATTR_ATTRIBUTION, SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
    )
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.util.dt import utcnow as dt_utcnow, as_local
from homeassistant.helpers.sun import get_astral_event_date

_INVERTERRT = 'http://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope={}&DeviceId={}&DataCollection=CommonInverterData'
_POWERFLOW_URL = 'http://{}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
#_INVERTERRT = 'http://{}?Scope={}&DeviceId={}&DataCollection=CommonInverterData'
#_POWERFLOW_URL = 'http://{}PowerFlow'
_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Fronius Inverter Data"

CONF_NAME = 'name'
CONF_IP_ADDRESS = 'ip_address'
CONF_DEVICE_ID = 'device_id'
CONF_SCOPE = 'scope'
CONF_UNITS = 'units'
CONF_POWERFLOW = 'powerflow'
CONF_START_TIME = 'start_time'
CONF_STOP_TIME = 'stop_time'

SCOPE_TYPES = ['Device', 'System']
UNIT_TYPES = ['Wh', 'kWh', 'MWh']

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)

# Key: ['device', json_key', 'name', unit, icon]
SENSOR_TYPES = {
    'ac_power': ['inverter', 'PAC', 'AC Power', 'W', 'mdi:solar-power'],
    'ac_current': ['inverter', 'IAC', 'AC Current', 'A', 'mdi:solar-power'],
    'ac_voltage': ['inverter', 'UAC', 'AC Voltage', 'V', 'mdi:solar-power'],
    'ac_frequency': ['inverter', 'FAC', 'AC Frequency', 'Hz', 'mdi:solar-power'],
    'dc_current': ['inverter', 'IDC', 'DC Current', 'A', 'mdi:solar-power'],
    'dc_voltage': ['inverter', 'UDC', 'DC Voltage', 'V', 'mdi:solar-power'],
    'day_energy': ['inverter', 'DAY_ENERGY', 'Day Energy', 'kWh', 'mdi:solar-power'],
    'year_energy': ['inverter', 'YEAR_ENERGY', 'Year Energy', 'Wh', 'mdi:solar-power'],
    'total_energy': ['inverter', 'TOTAL_ENERGY', 'Total Energy', 'Wh', 'mdi:solar-power'],
    'grid_usage': ['powerflow', 'P_Grid', 'Grid Usage', 'W', 'mdi:solar-power'],
    'house_load': ['powerflow', 'P_Load', 'House Load', 'W', 'mdi:solar-power'],
    'panel_status': ['powerflow', 'P_PV', 'Panel Status', 'W', 'mdi:solar-panel']
}

_SENSOR_TYPES_SYSTEM = {'ac_power', 'day_energy', 'year_energy', 'total_energy'}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_DEVICE_ID, default='1'): cv.string,
    vol.Optional(CONF_NAME, default='Fronius'): cv.string,
    vol.Optional(CONF_SCOPE, default='Device'):
        vol.In(SCOPE_TYPES),
    vol.Optional(CONF_UNITS, default='kWh'):
        vol.In(UNIT_TYPES),
    vol.Optional(CONF_START_TIME): cv.time,
    vol.Optional(CONF_STOP_TIME): cv.time,
    vol.Optional(CONF_POWERFLOW, default=False): cv.boolean,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Fronius inverter sensor."""

    ip_address = config[CONF_IP_ADDRESS]
    device_id = config.get(CONF_DEVICE_ID)
    scope = config.get(CONF_SCOPE)
    units = config.get(CONF_UNITS)
    name = config.get(CONF_NAME)
    powerflow = config.get(CONF_POWERFLOW)
    start_time = config.get(CONF_START_TIME)
    stop_time = config.get(CONF_STOP_TIME)

    inverter_data = InverterData(ip_address, device_id, scope)
    if powerflow:
        powerflow_data = PowerflowData(ip_address)

    try:
        inverter_data.update()
    except ValueError as err:
        _LOGGER.error("Received error from Fronius inverter: %s", err)
        return

    if powerflow:
        try:
            powerflow_data.update()
        except ValueError as err:
            _LOGGER.error("Received error from Fronius Powerflow: %s", err)
            return

    dev = []
    for variable in config[CONF_MONITORED_CONDITIONS]:
        if SENSOR_TYPES[variable][0] == "inverter":
            if scope == 'System' and variable in _SENSOR_TYPES_SYSTEM:
                dev.append(FroniusSensor(inverter_data, name, variable, scope, units, device_id, powerflow, start_time, stop_time))
            elif  scope == 'Device':
                dev.append(FroniusSensor(inverter_data, name, variable, scope, units, device_id, powerflow, start_time, stop_time))
        elif SENSOR_TYPES[variable][0] == "powerflow" and powerflow:
            dev.append(FroniusSensor(powerflow_data, name, variable, scope, units, device_id, powerflow, start_time, stop_time))

    add_entities(dev, True)

class FroniusSensor(Entity):
    """Implementation of the Fronius inverter sensor."""

    def __init__(self, device_data, name, sensor_type, scope, units, device_id, powerflow, start_time, stop_time):
        """Initialize the sensor."""
        self._client = name
        self._device = SENSOR_TYPES[sensor_type][0]
        self._json_key = SENSOR_TYPES[sensor_type][1]
        self._name = SENSOR_TYPES[sensor_type][2]
        self._type = sensor_type
        self._state = None
        self._device_id = device_id
        self._scope = scope
        self._units = units
        self._unit = SENSOR_TYPES[sensor_type][3]
        self._data = device_data
        self._icon = SENSOR_TYPES[sensor_type][4]
        self._powerflow = powerflow
        self._start_time = start_time
        self._stop_time = stop_time

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
        if self._unit == "Wh":
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

    def update(self, utcnow=None):
        """Get the latest data from inverter and update the states."""

        if utcnow is None:
            utcnow = dt_utcnow()
        now = as_local(utcnow)

        start_time = self.find_start_time(now)
        stop_time = self.find_stop_time(now)

        if start_time <= now <= stop_time:
            self._data.update()
            if not self._data:
                _LOGGER.info("Didn't receive data from the inverter")
                return
        else:
            _LOGGER.info("It's night time for the Fronius inverter")
            return

        # Prevent errors when data not present at night but retain long term states
        state = 0

        if self._data.latest_data and (self._json_key in self._data.latest_data):
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

        # convert and round the result
        if self._json_key == "YEAR_ENERGY" or self._json_key == "TOTAL_ENERGY":
            if self._units == "MWh":
                self._state = round(state / 1000000, 1)
            elif self._units == "kWh":
                self._state = round(state / 1000, 1)
            else:
                self._state = round(state, 1)
        elif self._json_key == "DAY_ENERGY":
            self._state = round(state / 1000, 1)
        else:
            self._state = round(state, 1)

        # Prevent these values going to zero if inverter is offline
        if (self._json_key == "YEAR_ENERGY" or self._json_key == "TOTAL_ENERGY") and state == 0:
            self._state = None

    def find_start_time(self, now):
        """Return sunrise or start_time if given."""
        if self._start_time:
            sunrise = now.replace(
                hour=self._start_time.hour, minute=self._start_time.minute,
                second=0)
        else:
            sunrise = get_astral_event_date(self.hass, SUN_EVENT_SUNRISE,
                                            now.date())
        return sunrise

    def find_stop_time(self, now):
        """Return dusk or stop_time if given."""
        if self._stop_time:
            sunset = now.replace(
                hour=self._stop_time.hour, minute=self._stop_time.minute,
                second=0)
        else:
            sunset = get_astral_event_date(self.hass, 'sunset', now.date())
        return sunset

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
    def update(self):
        """Get the latest data from inverter."""
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']
        except (KeyError, ConnectError, HTTPError, Timeout, ValueError) as error:
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
    def update(self):
        """Get the latest data from inverter."""
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']['Site']
        except (KeyError, ConnectError, HTTPError, Timeout, ValueError) as error:
            _LOGGER.error("Unable to connect to Fronius: %s", error)
            self._data = None
