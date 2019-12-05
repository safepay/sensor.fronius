[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)

[![Buy me a beer!](https://img.shields.io/badge/Buy%20me%20a%20beer!-%F0%9F%8D%BA-yellow.svg)](https://www.buymeacoffee.com/7PcGoSkb6)


# Fronius Sensor for Home Assistant
This component simplifies the integration of a Fronius inverter and optional PowerFlow:
* creates up to 12 individual sensors for easy display or use in automations
* converts Wh to kWh
* rounds values to 2 decimal places
* converts daily, yearly and total energy data to kWh or MWh (user-configurable)
* optionally connects to PowerFlow devices for 3 additional sensors
* optionally converts PowerFlow units to W, kW or MW
* optionally sums values if you have more than one inverter
* compatible with the custom [Power Wheel Card](https://github.com/gurbyz/power-wheel-card/tree/master) if using PowerFlow

### URL's Utilised
The Default URL called is ``http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData``

The optional PowerFlow URL is ``http://ip_address/solar_api/v1/GetPowerFlowRealtimeData.fcgi``

### Installation
Copy the ``fronius_inverter`` folder in the custom_components directory into your own custom_components directory in your config directory of Home Assistant.

E.g.:
```
../config/custom_components/fronius_inverter/__init__.py
../config/custom_components/fronius_inverter/manifest.json
../config/custom_components/fronius_inverter/sensor.py
```

Be sure to pull raw data from GitHub or use [HACS](https://custom-components.github.io/hacs/)

### Configuration
```yaml
# Minimal configuration.yaml entry:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
```

```yaml
# Example configuration.yaml entry where you can specify the sensors you want:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    monitored_conditions:
      - ac_power
      - day_energy
      - year_energy
      - total_energy
```

```yaml
# Example configuration.yaml entry where you have more than one inverter:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    scope: System
```

```yaml
# Example configuration.yaml entry where you have a PowerFlow device:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    powerflow: True
    power_units: kW
```

### Configuration Variables

variable | required | type | default | description
-------- | -------- | ---- | ------- | -----------
``ip_address`` | yes | string | | The local IP address of your Fronius Inverter.
``name`` | no | string | ``Fronius`` | The preferred name of your Fronius Inverter.
``powerflow`` | no | boolean | ``False`` | Set to ``True`` if you have a PowerFlow meter to add ``grid_usage``, ``house_load`` and ``panel_status`` sensors.
``units`` | no | string | ``MWh`` | The preferred units for Year and Total Energy from ``Wh, kWh, MWh``.
``power_units`` | no | string | ``W`` | The preferred PowerFlow units from ``W, kW, MW``.
``device_id`` | no | string | ``1`` | The Device ID of your Fronius Inverter.
``scope`` | no | string | ``Device`` | Set to ``System`` if you have multiple inverters. This will return ``ac_power, daily_energy, year_energy`` and, ``total_energy`` only. Case-sensitive.
``scan_interval`` | no | integer | ``60`` | Minimum configurable number of seconds between polls.
``monitored_conditions`` | no | list | All | List of monitored conditions from: ``ac_power``, ``ac_current``, ``ac_voltage``, ``ac_frequency``, ``dc_current``, ``dc_energy``, ``daily_energy``, ``year_energy``, ``total_energy``


### Custom Power Wheel Card (if using a Powerflow)

Follow the instructions for installation on [Github](https://github.com/gurbyz/power-wheel-card/tree/master)

Add the following to the top of your Lovelace config in the Raw Config Editor:
```yaml
resources:
  - type: module
    url: /local/custom_ui/power-wheel-card.js?v=1
```
Then add and configure a basic custom  card:
```yaml
type: 'custom:power-wheel-card'
title: Solar Power
production_is_positive: false
solar_power_entity: sensor.fronius_panel_status
grid_power_entity: sensor.fronius_grid_usage
home_energy_entity: sensor.fronius_house_load
```
