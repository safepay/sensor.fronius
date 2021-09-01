"""Support for the Fronius Inverter."""
import logging
from datetime import timedelta

import requests
import voluptuous as vol
import json
import aiohttp
import asyncio

from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_SCAN_INTERVAL, ATTR_ATTRIBUTION, SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET, STATE_UNAVAILABLE, DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR, ENERGY_WATT_HOUR, DEVICE_CLASS_POWER, POWER_KILO_WATT, POWER_WATT, DEVICE_CLASS_CURRENT, DEVICE_CLASS_VOLTAGE
)

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA, STATE_CLASS_MEASUREMENT, STATE_CLASS_TOTAL_INCREASING, SensorEntity,
)

from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import Entity
from homeassistant.util.dt import utcnow as dt_utcnow, as_local
from homeassistant.util import dt as dt_util
from homeassistant.helpers.sun import get_astral_event_date

_INVERTERRT_URL = 'http://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope={}&DeviceId={}&DataCollection=CommonInverterData'
_POWERFLOW_URL = 'http://{}/solar_api/v1/GetPowerFlowRealtimeData.fcgi'
_METER_URL = 'http://{}/solar_api/v1/GetMeterRealtimeData.cgi?Scope={}&DeviceId={}'
#_INVERTERRT_URL = 'http://{}{}?DeviceId={}&DataCollection=CommonInverterData'
#_POWERFLOW_URL = 'http://{}PowerFlow'
_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Fronius Inverter Data"

CONF_NAME = 'name'
CONF_IP_ADDRESS = 'ip_address'
CONF_MODEL = 'model'
CONF_DEVICE_ID = 'device_id'
CONF_SCOPE = 'scope'
CONF_UNITS = 'units'
CONF_POWER_UNITS = 'power_units'
CONF_POWERFLOW = 'powerflow'
CONF_SMARTMETER = 'smartmeter'
CONF_SMARTMETER_DEVICE_ID = 'smartmeter_device_id'
CONF_ALWAYS_LOG = 'always_log'

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

SCOPE_TYPES = ['Device', 'System']
UNIT_TYPES = ['Wh', 'kWh', 'MWh']
POWER_UNIT_TYPES = ['W', 'kW', 'MW']
MODEL_TYPES = ['symo', 'gen24']

# Key: ['device', 'system', 'json_key', 'name', 'unit', 'convert_units', 'icon']
SENSOR_TYPES = {
    'year_energy': ['inverter', True, 'YEAR_ENERGY', 'Year Energy', 'MWh', 'energy', 'mdi:solar-power'],
    'total_energy': ['inverter', True, 'TOTAL_ENERGY', 'Total Energy', 'MWh', 'energy', 'mdi:solar-power'],
    'ac_power': ['inverter', True, 'PAC', 'AC Power', 'W', 'power', 'mdi:solar-power'],
    'day_energy': ['inverter', True, 'DAY_ENERGY', 'Day Energy', 'kWh', 'energy', 'mdi:solar-power'],
    'ac_current': ['inverter', False, 'IAC', 'AC Current', 'A', False, 'mdi:solar-power'],
    'ac_voltage': ['inverter', False, 'UAC', 'AC Voltage', 'V', False, 'mdi:solar-power'],
    'ac_frequency': ['inverter', False, 'FAC', 'AC Frequency', 'Hz', False, 'mdi:solar-power'],
    'dc_current': ['inverter', False, 'IDC', 'DC Current', 'A', False, 'mdi:solar-power'],
    'dc_voltage': ['inverter', False, 'UDC', 'DC Voltage', 'V', False, 'mdi:solar-power'],
    'grid_usage': ['powerflow', False, 'P_Grid', 'Grid Usage', 'W', 'power', 'mdi:solar-power'],
    'house_load': ['powerflow', False, 'P_Load', 'House Load', 'W', 'power', 'mdi:solar-power'],
    'panel_status': ['powerflow', False, 'P_PV', 'Panel Status', 'W', 'power', 'mdi:solar-panel'],
    'rel_autonomy': ['powerflow', False, 'rel_Autonomy', 'Relative Autonomy', '%', False, 'mdi:solar-panel'],
    'rel_selfconsumption': ['powerflow', False, 'rel_SelfConsumption', ' Relative Self Consumption', '%', False, 'mdi:solar-panel'],
    'smartmeter_current_ac_phase_one': ['smartmeter', False, 'Current_AC_Phase_1', 'SmartMeter Current AC Phase 1', 'A', False, 'mdi:solar-power'],
    'smartmeter_current_ac_phase_two': ['smartmeter', False, 'Current_AC_Phase_2', 'SmartMeter Current AC Phase 2', 'A', False, 'mdi:solar-power'],
    'smartmeter_current_ac_phase_three': ['smartmeter', False, 'Current_AC_Phase_3', 'SmartMeter Current AC Phase 3', 'A', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_one': ['smartmeter', False, 'Voltage_AC_Phase_1', 'SmartMeter Voltage AC Phase 1', 'V', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_two': ['smartmeter', False, 'Voltage_AC_Phase_2', 'SmartMeter Voltage AC Phase 2', 'V', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_three': ['smartmeter', False, 'Voltage_AC_Phase_3', 'SmartMeter Voltage AC Phase 3', 'V', False, 'mdi:solar-power'],
    'smartmeter_energy_ac_consumed': ['smartmeter', False, 'EnergyReal_WAC_Sum_Consumed', 'SmartMeter Energy AC Consumed', 'Wh', 'energy', 'mdi:solar-power'],
    'smartmeter_energy_ac_sold': ['smartmeter', False, 'EnergyReal_WAC_Sum_Produced', 'SmartMeter Energy AC Sold', 'Wh', 'energy', 'mdi:solar-power']
}
# the gen24 inverter has different names for some sensors
SENSOR_TYPES_GEN24 = {
    'smartmeter_current_ac_phase_one': ['smartmeter', False, 'ACBRIDGE_CURRENT_ACTIVE_MEAN_01_F32', 'SmartMeter Current AC Phase 1', 'A', False, 'mdi:solar-power'],
    'smartmeter_current_ac_phase_two': ['smartmeter', False, 'ACBRIDGE_CURRENT_ACTIVE_MEAN_02_F32', 'SmartMeter Current AC Phase 2', 'A', False, 'mdi:solar-power'],
    'smartmeter_current_ac_phase_three': ['smartmeter', False, 'ACBRIDGE_CURRENT_ACTIVE_MEAN_03_F32', 'SmartMeter Current AC Phase 3', 'A', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_one': ['smartmeter', False, 'SMARTMETER_VOLTAGE_01_F64', 'SmartMeter Voltage AC Phase 1', 'V', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_two': ['smartmeter', False, 'SMARTMETER_VOLTAGE_02_F64', 'SmartMeter Voltage AC Phase 2', 'V', False, 'mdi:solar-power'],
    'smartmeter_voltage_ac_phase_three': ['smartmeter', False, 'SMARTMETER_VOLTAGE_03_F64', 'SmartMeter Voltage AC Phase 3', 'V', False, 'mdi:solar-power'],
    'smartmeter_energy_ac_consumed': ['smartmeter', False, 'SMARTMETER_ENERGYACTIVE_CONSUMED_SUM_F64', 'SmartMeter Energy AC Consumed', 'Wh', 'energy', 'mdi:solar-power'],
    'smartmeter_energy_ac_sold': ['smartmeter', False, 'SMARTMETER_ENERGYACTIVE_PRODUCED_SUM_F64', 'SmartMeter Energy AC Sold', 'Wh', 'energy', 'mdi:solar-power']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_MODEL, default="symo"):
        vol.In(MODEL_TYPES),
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
    vol.Optional(CONF_SMARTMETER, default=False): cv.boolean,
    vol.Optional(CONF_SMARTMETER_DEVICE_ID, default='0'): cv.string,
    vol.Optional(CONF_ALWAYS_LOG, default=True): cv.boolean,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Fronius inverter sensor."""

    session = async_get_clientsession(hass)
    ip_address = config[CONF_IP_ADDRESS]
    model = config[CONF_MODEL]
    device_id = config.get(CONF_DEVICE_ID)
    scope = config.get(CONF_SCOPE)
    units = config.get(CONF_UNITS)
    power_units = config.get(CONF_POWER_UNITS)
    name = config.get(CONF_NAME)
    powerflow = config.get(CONF_POWERFLOW)
    smartmeter = config.get(CONF_SMARTMETER)
    smartmeter_device_id = config.get(CONF_SMARTMETER_DEVICE_ID)
    scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    always_log = config.get(CONF_ALWAYS_LOG)

    if model == 'gen24':
        _LOGGER.debug("GEN24 configured, updating sensor list")
        # update sensors since gen24 has different names for some of them
        for variable in SENSOR_TYPES:
            if variable in SENSOR_TYPES_GEN24:
                SENSOR_TYPES[variable] = SENSOR_TYPES_GEN24[variable]
    _LOGGER.debug(SENSOR_TYPES)

    fetchers = []
    inverter_data = InverterData(session, ip_address, device_id, scope)
    fetchers.append(inverter_data)
    if powerflow:
        powerflow_data = PowerflowData(session, ip_address, None, None)
        fetchers.append(powerflow_data)
    if smartmeter:
        smartmeter_data = SmartMeterData(session, ip_address, smartmeter_device_id, "Device")
        fetchers.append(smartmeter_data)

    def fetch_executor(fetcher):
        async def fetch_data(*_):
            await fetcher.async_update()
        return fetch_data

    for fetcher in fetchers:
        fetch = fetch_executor(fetcher)
        await fetch()
        async_track_time_interval(hass, fetch, scan_interval)

    dev = []
    for variable in config[CONF_MONITORED_CONDITIONS]:

        device = SENSOR_TYPES[variable][0]
        system = SENSOR_TYPES[variable][1]
        sensor_units = SENSOR_TYPES[variable][4]
        convert_units = SENSOR_TYPES[variable][5]

        if convert_units == 'power':
            sensor_units = power_units
        elif convert_units == 'energy':
            sensor_units = units

        sensor = "sensor." + name + "_" + SENSOR_TYPES[variable][3]
        state = hass.states.get(sensor)

        if device == "inverter":
            _LOGGER.debug("Adding inverter sensor: {}, {}, {}, {}, {}, {}, {}, {}".format(inverter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            dev.append(FroniusSensor(inverter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter, always_log))

        elif device == "powerflow" and powerflow:
            _LOGGER.debug("Adding powerflow sensor: {}, {}, {}, {}, {}, {}, {}, {}".format(powerflow_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            dev.append(FroniusSensor(powerflow_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter, always_log))

        elif device == "smartmeter" and smartmeter:
            _LOGGER.debug("Adding meter sensor: {}, {}, {}, {}, {}, {}, {}, {}".format(smartmeter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            dev.append(FroniusSensor(smartmeter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter, always_log))

    async_add_entities(dev, True)

class FroniusSensor(SensorEntity):
    """Implementation of the Fronius inverter sensor."""

    def __init__(self, device_data, name, sensor_type, scope, units, device_id, powerflow, smartmeter, always_log):
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
        self._smartmeter = smartmeter
        self._always_log = always_log

        # add attributes to support Energy dashboard and statistics for power sensors, new in HA 2021.8
        # and updated in 2021.9 due to bugs in the orginal HA implementation.
        # ref https://developers.home-assistant.io/docs/core/entity/sensor/
        if self._convert_units == "power":
            self._attr_device_class = DEVICE_CLASS_POWER
            self._attr_state_class = STATE_CLASS_MEASUREMENT
        elif self._convert_units == "energy":
            self._attr_device_class = DEVICE_CLASS_ENERGY
            self._attr_state_class = STATE_CLASS_TOTAL_INCREASING

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._client, self._name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def available(self, utcnow=None):
        if self._always_log:
            return True

        if utcnow is None:
            utcnow = dt_utcnow()
        now = as_local(utcnow)

        start_time = self.find_start_time(now)
        stop_time = self.find_stop_time(now)

        if as_local(start_time) <= now <= as_local(stop_time):
            _LOGGER.debug("Sensor is running. Start/Stop time: {}, {}".format(as_local(start_time), as_local(stop_time)))
            return True
        else:
            _LOGGER.debug("Sensor is not running. Start/Stop time: {}, {}".format(as_local(start_time), as_local(stop_time)))
            return False

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self._client} {self._name}"

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

    @property
    def should_poll(self):
        """Device should not be polled, returns False."""
        return False

    async def async_update(self, utcnow=None):
        """Get the latest data from inverter and update the states."""
        if not self.available:
            self._state = STATE_UNAVAILABLE
            return

        state = None
        if self._data.latest_data and (self._json_key in self._data.latest_data):
            _LOGGER.debug("Device: {}".format(self._device))
            if self._device == 'inverter':
                # Read data, if a value is 'null' convert it to 0
                if self._scope == 'Device':
                    state = self._data.latest_data[self._json_key]['Value']
                    if state is None:
                        _LOGGER.debug(">>>>> Converting {} from null to 0".format(self._json_key))
                        state = 0
                elif self._scope == 'System':
                    for item in self._data.latest_data[self._json_key]['Values']:
                        value = self._data.latest_data[self._json_key]['Values'][item]
                        if value is None:
                            _LOGGER.debug(">>>>> Converting {} from null to 0".format(self._json_key))
                            value = 0
                        state = state + value
            elif self._device == 'powerflow' or self._device == 'smartmeter':
                # Read data directly, if it is 'null' convert it to 0
                state = self._data.latest_data[self._json_key]
                if state is None:
                    _LOGGER.debug(">>>>> Converting {} from null to 0".format(self._json_key))
                    state = 0
            _LOGGER.debug("State: {}".format(state))

        # convert and round the result
        if state is not None:
            _LOGGER.debug("Sensor: {}".format(self._json_key))
            if self._convert_units == "energy":
                _LOGGER.debug("Converting energy ({}) to {}".format(state, self._units))
                if self._units == "MWh":
                    self._state = round(state / 1000000, 2)
                elif self._units == "kWh":
                    self._state = round(state / 1000, 2)
                else:
                    self._state = round(state, 2)
            elif self._convert_units == "power":
                _LOGGER.debug("Converting power ({}) to {}".format(state, self._units))
                if self._units == "MW":
                    self._state = round(state / 1000000, 2)
                elif self._units == "kW":
                    self._state = round(state / 1000, 2)
                else:
                    self._state = round(state, 2)
            elif self._json_key == "DAY_ENERGY":
                # day energy always gets converted to kWh
                _LOGGER.debug("Converting day energy to kWh ({})".format(state))
                self._state = round(state / 1000, 2)
            else:
                _LOGGER.debug("Rounding ({}) to two decimals".format(state))
                self._state = round(state, 2)
        else:
            _LOGGER.debug(">>>>> State is None for {} <<<<<".format(self._json_key))
            _LOGGER.debug("Latest data: {}".format(self._data.latest_data))
        _LOGGER.debug("State converted ({})".format(self._state))

    async def async_added_to_hass(self):
        """Register at data provider for updates."""
        await self._data.register(self)

    def __hash__(self):
        """Hash sensor by hashing its name."""
        return hash(self.name)

    def find_start_time(self, now):
        """Return sunrise or start_time if given."""
        sunrise = get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, now.date())
        return sunrise

    def find_stop_time(self, now):
        """Return sunset or stop_time if given."""
        sunset = get_astral_event_date(self.hass, SUN_EVENT_SUNSET, now.date())
        return sunset

class FroniusFetcher:
    """Handle Fronius API requests."""

    def __init__(self, session, ip_address, device_id, scope):
        """Initialize the data object."""
        self._session = session
        self._ip_address = ip_address
        self._device_id = device_id
        self._scope = scope
        self._data = None
        self._sensors = set()

    async def async_update(self):
        """Retrieve and update latest state."""
        try:
            await self._update()
        except aiohttp.ClientConnectionError:
            _LOGGER.error("Failed to update: connection error")
        except asyncio.TimeoutError:
            _LOGGER.error("Failed to update: request timeout")
        except ValueError:
            _LOGGER.error("Failed to update: invalid response received")

        # Schedule an update for all included sensors
        for sensor in self._sensors:
            sensor.async_schedule_update_ha_state(True)

    async def fetch_data(self, url):
        """Retrieve data from inverter in async manner."""
        _LOGGER.debug("Requesting data from URL: %s", url)
        try:
            response = await self._session.get(url, timeout=10)
            if response.status != 200:
                raise ValueError
            json_response = await response.json()
            _LOGGER.debug("Got data from URL: %s\n%s", url, json_response)
            return json_response
        except aiohttp.ClientResponseError:
            raise ValueError

    @property
    def latest_data(self):
        """Return the latest data object."""
        if self._data:
            return self._data
        return None

    async def register(self, sensor):
        """Register child sensor for update subscriptions."""
        self._sensors.add(sensor)

class InverterData(FroniusFetcher):
    """Handle Fronius API object and limit updates."""

    def _build_url(self):
        """Build the URL for the requests."""
        url = _INVERTERRT_URL.format(self._ip_address, self._scope, self._device_id)
        _LOGGER.debug("Fronius Inverter URL: %s", url)
        return url

    async def _update(self):
        """Get the latest data from inverter."""
        _LOGGER.debug("Requesting inverter data")
        self._data = (await self.fetch_data(self._build_url()))['Body']['Data']

class PowerflowData(FroniusFetcher):
    """Handle Fronius API object and limit updates."""

    def _build_url(self):
        """Build the URL for the requests."""
        url = _POWERFLOW_URL.format(self._ip_address)
        _LOGGER.debug("Fronius Powerflow URL: %s", url)
        return url

    async def _update(self):
        """Get the latest data from inverter."""
        _LOGGER.debug("Requesting powerflow data")
        self._data = (await self.fetch_data(self._build_url()))['Body']['Data']['Site']

class SmartMeterData(FroniusFetcher):
    """Handle Fronius API object and limit updates."""

    def _build_url(self):
        """Build the URL for the requests."""
        url = _METER_URL.format(self._ip_address, self._scope, self._device_id)
        _LOGGER.debug("Fronius SmartMeter URL: %s", url)
        return url

    async def _update(self):
        """Get the latest data from inverter."""
        _LOGGER.debug("Requesting smartmeter data")
        self._data = (await self.fetch_data(self._build_url()))['Body']['Data']
