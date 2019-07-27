[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)

[![Buy me a beer!](https://img.shields.io/badge/Buy%20me%20a%20beer!-%F0%9F%8D%BA-yellow.svg)](https://www.buymeacoffee.com/7PcGoSkb6)


# Fronius Sensor for Home Assistant
This component simplifies the integration of a Fronius inverter:
* creates up to 12 individual sensors for easy display or use in automations
* converts Wh to kWh
* rounds values to 2 decimal places
* converts yearly and total energy data to kWh or MWh (user-configurable)
* optionally connects to PowerFlow devices for 3 additional sensors
* optionally sums values if you have more than one inverter
* pauses from sunset to sunrise to handle inverters going offline at night

### URL's Utilised
The Default URL called is ``http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData``

The optional PowerFlow URL is ``http://ip_address/solar_api/v1/GetPowerFlowRealtimeData.fcgi``

### Getting Your System to Report
If your inverter has a different id than "1" then pass your device ID as "device_id" as per the configuration.

If you have multiple inverters, set ``scope: System`` as per the configuration below to return summed values for all inverters.

### Handling Inverter Offline at Night
Fronius inverters shut down their API endpoints at night by default.

This component will not poll the inverter from sunset to sunrise.

This means that if you restart HA at night, you will get "-" for all sensors until the inverter is back online the next morning. If left runnings, the state of the sensors will remain unchanged from senset until the next sunrise.

You can override these times with ``start_time`` and ``stop_time``.

## Installation
Copy the ``fronius_inverter`` folder in the custom_components directory into your own custom_components directory in your config directory of Home Assistant.

E.g.:
```
../config/custom_components/fronius_inverter/__init__.py
../config/custom_components/fronius_inverter/manifest.json
../config/custom_components/fronius_inverter/sensor.py
```

Be sure to pull raw data from GitHub or use [HACS](https://custom-components.github.io/hacs/)

## Configuration
```
# Minimal configuration.yaml entry:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
```

```
# Example configuration.yaml entry where you can specify the sensors you want:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    device_id: 1
    powerflow: True
    monitored_conditions:
      - ac_power
      - ac_current
      - ac_voltage
      - ac_frequency
      - dc_current
      - dc_voltage
      - day_energy
      - year_energy
      - total_energy
      - grid_usage
      - house_load
      - panel_status
```

```
# Example configuration.yaml entry where you have more than one inverter:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    scope: System
```
### CONFIGURATION VARIABLES

key | required | type | default | description
--- | -------- | ---- | ------- | -----------
``ip_address`` | yes | string | | The local IP address of your Fronius Inverter.
``name`` | no | string | ``Fronius`` | The preferred name of your Fronius Inverter.
``powerflow`` | no | boolean | ``False`` | Set to True if you have a PowerFlow meter to add ``grid_usage, house_load`` and ``panel_status`` sensors.
``units`` | no | string | ``MWh`` | The preferred units for Year and Total Energy from ``Wh, kWh, MWh``.
``device_id`` | no | string | ``1`` | The Device ID of your Fronius Inverter.
``scope`` | no | string | ``Device`` | Set to ``System`` if you have multiple inverters. This will return ``ac_power, daily_energy, year_energy`` and, ``total_energy`` only. Case-sensitive.
``start_time`` | no | time | ``sunrise`` | Hours and minutes for the start of logging. E.g. ``'7:30'``
``end_time`` | no | time | ``sunset`` | Hours and minutes for the end of logging. E.g. ``'18:00'``
``scan_interval`` | no | integer | ``300`` | Minimum configurable number of seconds between polls.
``monitored_conditions`` | no | list | All | List of monitored conditions from: ``ac_power, ac_current, ac_voltage, ac_frequency, dc_current, dc_energy, daily_energy, year_energy, total_energy``


