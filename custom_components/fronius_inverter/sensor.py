"""Support for the Fronius Inverter."""
import logging
from datetime import timedelta

import requests
import voluptuous as vol
import json

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
_METER_URL = 'http://{}/solar_api/v1/GetMeterRealtimeData.cgi?Scope={}&DeviceId={}'
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
CONF_SMARTMETER = 'smartmeter'
CONF_SMARTMETER_DEVICE_ID = 'smartmeter_device_id'

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
    vol.Optional(CONF_SMARTMETER, default=False): cv.boolean,
    vol.Optional(CONF_SMARTMETER_DEVICE_ID, default='0'): cv.string,
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
    smartmeter = config.get(CONF_SMARTMETER)
    smartmeter_device_id = config.get(CONF_SMARTMETER_DEVICE_ID)

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
    
    if smartmeter:
        smartmeter_data = SmartMeterData(ip_address, smartmeter_device_id)
        try:
            await smartmeter_data.async_update()
        except ValueError as err:
            _LOGGER.error("Received data error from Fronius SmartMeter: %s", err)
            return


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
            dev.append(FroniusSensor(inverter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            
        elif device == "powerflow" and powerflow:
            _LOGGER.debug("Adding powerflow sensor: {}, {}, {}, {}, {}, {}, {}, {}".format(powerflow_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            dev.append(FroniusSensor(powerflow_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
        
        elif device == "smartmeter" and smartmeter:
            _LOGGER.debug("Adding meter sensor: {}, {}, {}, {}, {}, {}, {}, {}".format(smartmeter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))
            dev.append(FroniusSensor(smartmeter_data, name, variable, scope, sensor_units, device_id, powerflow, smartmeter))

    async_add_entities(dev, True)

class FroniusSensor(Entity):
    """Implementation of the Fronius inverter sensor."""

    def __init__(self, device_data, name, sensor_type, scope, units, device_id, powerflow, smartmeter):
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
        if utcnow is None:
            utcnow = dt_utcnow()
        now = as_local(utcnow)

        start_time = self.find_start_time(now)
        stop_time = self.find_stop_time(now)

        _LOGGER.debug("!!! Start Time, Stop Time, Device: {}, {}, {}".format(as_local(start_time), as_local(stop_time), self._device))

        return True

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

    def find_start_time(self, now):
        """Return sunrise or start_time if given."""
        sunrise = get_astral_event_date(self.hass, SUN_EVENT_SUNRISE, now.date())
        return sunrise

    def find_stop_time(self, now):
        """Return sunset or stop_time if given."""
        sunset = get_astral_event_date(self.hass, SUN_EVENT_SUNSET, now.date())
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
    async def async_update(self):
        """Get the latest data from inverter."""
        _LOGGER.debug("Requesting inverter data")
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
        _LOGGER.debug("Requesting powerflow data")
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']['Site']
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to Powerflow: %s", error)
            self._data = None

class SmartMeterData:
    """Handle Fronius API object and limit updates."""

    def __init__(self, ip_address, device_id):
        """Initialize the data object."""
        self._ip_address = ip_address
        self._device_id = device_id
        self._scope = 'Device'

    def _build_url(self):
        """Build the URL for the requests."""
        url = _METER_URL.format(self._ip_address, self._scope, self._device_id)
        _LOGGER.debug("Fronius SmartMeter URL: %s", url)
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
        _LOGGER.debug("Requesting smartmeter data")
        try:
            result = requests.get(self._build_url(), timeout=10).json()
            self._data = result['Body']['Data']
        except (requests.exceptions.RequestException) as error:
            _LOGGER.error("Unable to connect to Meter: %s", error)
            self._data = None
