[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)

[![Buy me a beer!](https://img.shields.io/badge/Buy%20me%20a%20beer!-%F0%9F%8D%BA-yellow.svg)](https://www.buymeacoffee.com/7PcGoSkb6)


# Fronius Sensor for Home Assistant

This Fronius sensor creates up to 12 individual sensors in HA and converts Wh to kWh or MWh for easy display or use in automations.

It works by reading data from Fronius inverters and, optionally, from PowerFlow devices.

### URL's Utilised
The Default URL called is ``http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData``

The optional PowerFlow URL is ``http://ip_address/solar_api/v1/GetPowerFlowRealtimeData.fcgi``

### Getting Your System to Report
If your inverter has a different id than "1" then pass your device ID as "device_id" as per the configuration.

If you have multiple inverters, set ``scope: System`` as per the configuration below to return summed values for all inverters.

### Handling Inverter Offline at Night
Fronius inverters shut down their API endpoints at night by default.

This component will set all values to 0 (Zero) during that time except for the Yearly and Lifetime totals.

This means that if you restart HA at night, you will get zeros for all values and "-" for Yearly and Lifetime until the inverter is back online the next morning.

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
``units`` | no | string | ``kWh`` | The preferred units for Year and Total Energy from ``Wh, kWh, MWh``.
``device_id`` | no | string | ``1`` | The Device ID of your Fronius Inverter.
``scope`` | no | string | ``Device`` | Set to ``System`` if you have multiple inverters. This will return ``ac_power, daily_energy, year_energy`` and, ``total_energy`` only. Case-sensitive.
``start_time`` | no | time | ``sunrise`` | Hours and minutes for the start of logging. E.g. ``'7:30'``
``end_time`` | no | time | ``sunset`` | Hours and minutes for the end of logging. E.g. ``'18:00'``
``scan_interval`` | no | integer | ``300`` | Number of seconds between polls.
``monitored_conditions`` | no | list | All | List of monitored conditions from: ``ac_power, ac_current, ac_voltage, ac_frequency, dc_current, dc_energy, daily_energy, year_energy, total_energy``


