[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius) ![Maintenance](https://img.shields.io/maintenance/no/2020.svg)

# Fronius Sensor for Home Assistant
This component simplifies the integration of a Fronius inverter and optional PowerFlow/SmartMeter:
* creates up to 22 individual sensors for easy display or use in automations
* converts Wh to kWh
* rounds values to 2 decimal places
* converts yearly and total energy data to kWh or MWh (user-configurable)
* optionally sums values if you have more than one inverter

If you have a SmartMeter installed this component:
* optionally connects to PowerFlow API for 5 additional sensors
* optionally connects to SmartMeter API for 8 additional sensors
* optionally converts PowerFlow units to W, kW or MW
* compatible with the custom [Power Wheel Card](https://github.com/gurbyz/power-wheel-card/tree/master) if using PowerFlow

### Energy dashboard support - HA 2021.8+
All energy and power sensors provide required attributes to allow long term statistics to be recorded which enables support for the new Energy dashboard introduced in HA 2021.8. The following "lifetime" sensors can be added to the energy configuration:

* Solar production: ``total_energy``
* Grid consumption: ``smartmeter_energy_ac_consumed``
* Grid feed-in: ``smartmeter_energy_ac_sold``

### URL's Utilised
The Default URL called is ``http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData``

The optional PowerFlow URL is ``http://ip_address/solar_api/v1/GetPowerFlowRealtimeData.fcgi``

The optional SmartMeter URL is ``http://ip_address/solar_api/v1/GetMeterRealtimeData.cgi?Scope=Device&DeviceId=1``

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
# Example configuration.yaml entry where you have a SmartMeter device and add PowerFlow sensors:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    powerflow: True
    power_units: kW
```

```yaml
# Example configuration.yaml entry where you have a SmartMeter device and add SmartMeter sensors:
sensor:
  - platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
    smartmeter: True
```

### Configuration Variables

variable | required | type | default | description
-------- | -------- | ---- | ------- | -----------
``ip_address`` | yes | string | | The local IP address of your Fronius Inverter.
``name`` | no | string | ``Fronius`` | The preferred name of your Fronius Inverter.
``always_log`` | no | boolean | ``True`` | Set to ``False`` if your Fronius Inverter shuts down when the sun goes down.
``scan_interval`` | no | string | 60 | The interval to query the Fronius Inverter for data.
``powerflow`` | no | boolean | ``False`` | Set to ``True`` if you have a PowerFlow meter (SmartMeter) to add ``grid_usage``, ``house_load``, ``panel_status``, ``rel_autonomy`` and ``rel_selfconsumption`` sensors.
``smartmeter`` | no | boolean | ``False`` | Set to ``True`` if you have a SmartMeter to add ``smartmeter_current_ac_phase_one``, ``smartmeter_current_ac_phase_two``, ``smartmeter_current_ac_phase_three``, ``smartmeter_voltage_ac_phase_one``, ``smartmeter_voltage_ac_phase_two``, ``smartmeter_voltage_ac_phase_three``, ``smartmeter_energy_ac_consumed`` and ``smartmeter_energy_ac_sold`` sensors.
``smartmeter_device_id`` | no | string | ``0`` | The Device ID of your Fronius SmartMeter.
``units`` | no | string | ``MWh`` | The preferred units for Year and Total Energy from ``Wh, kWh, MWh``.
``power_units`` | no | string | ``W`` | The preferred PowerFlow units from ``W, kW, MW``.
``device_id`` | no | string | ``1`` | The Device ID of your Fronius Inverter.
``scope`` | no | string | ``Device`` | Set to ``System`` if you have multiple inverters. This will return ``ac_power, day_energy, year_energy`` and, ``total_energy`` only. Case-sensitive.
``monitored_conditions`` | no | list | All | List of monitored conditions from: ``ac_power``, ``ac_current``, ``ac_voltage``, ``ac_frequency``, ``dc_current``, ``dc_voltage``, ``day_energy``, ``year_energy``, ``total_energy``, ``grid_usage``, ``house_load``, ``panel_status``, ``rel_autonomy``, ``rel_selfconsumption``, ``smartmeter_current_ac_phase_one``, ``smartmeter_current_ac_phase_two``, ``smartmeter_current_ac_phase_three``, ``smartmeter_voltage_ac_phase_one``, ``smartmeter_voltage_ac_phase_two``, ``smartmeter_voltage_ac_phase_three``, ``smartmeter_energy_ac_consumed``, ``smartmeter_energy_ac_sold``


### Custom Power Wheel Card (if using a Powerflow)

Follow the instructions for installation on [Github](https://github.com/gurbyz/power-wheel-card/tree/master)

Add the following to the Lovelace resource config in the Raw Config Editor:
```yaml
resources:
  - type: module
    url: /local/custom_ui/power-wheel-card.js?v=1
```
Then add and configure a basic custom card for displaying the power view:
```yaml
type: 'custom:power-wheel-card'
title: Solar Power
production_is_positive: false
solar_power_entity: sensor.fronius_panel_status
grid_power_entity: sensor.fronius_grid_usage
```

If you also want to have an energy view in the Power Wheel you need three more sensors. And these sensors
will be different depending on if your smart meter is installed in the feed-in-path or consumption-path.

This is the configuration you need to add to your Power Wheel config in Lovelace. This will be the same
regardless of where your smart meter is installed.
```yaml
solar_energy_entity: sensor.fronius_day_energy
grid_energy_consumption_entity: sensor.grid_consumed_energy_day
grid_energy_production_entity: sensor.grid_sold_energy_day
```

Next you need to create two new sensors for grid energy consumption and production. And this is what
will differ depending on your smart meter installation.

1. **Feed-in path.** This is the simplest setup. With the smart meter in the feed-in path (next to your main
electricity meter) it already knows what you are consuming and producing. But it counts the accumulative
values. And we need daily vaules, in kWh, to match the sensor.fronius_day_energy.

Create the two sensors for daily consumption and production.
Note: if smart meter energy sensors are not in kWh you need to convert those two to kWh using template sensors.
```yaml
utility_meter:
  # calculate daily energy consumed from grid (input must be in kWh)
  grid_consumed_energy_day:
    source: sensor.fronius_smartmeter_energy_ac_consumed
    cycle: daily
  # calculate daily energy sold to grid (input must be in kWh)
  grid_sold_energy_day:
    source: sensor.fronius_smartmeter_energy_ac_sold
    cycle: daily
```

2. **Consumption path.** With the smart meter in the consumption path (between the inverter and your consumers)
it cannot know how much you are consuming or producing from/to the grid. So the only sensor that will have
a value is the sensor.fronius_smartmeter_energy_ac_consumed. But it will not show what is consumed from the
grid. It will show how much your house has consumed. So we need to create sensors that will give us what
the Power Wheel needs.
```yaml
utility_meter:
  # convert consumed energy to daily energy (this is what the house consumes)
  house_energy_day:
    source: sensor.fronius_smartmeter_energy_ac_consumed
    cycle: daily
```
```yaml
sensor:
  - platform: template
    sensors:
      # calculate grid energy (negative will be to grid, positive from grid)
      grid_energy_day:
        friendly_name: 'Grid energy'
        unit_of_measurement: 'kWh'
        value_template: '{{ (states("sensor.fronius_day_energy") | float - states("sensor.house_energy_day") | float) * -1 }}'
      # calculate energy consumed from grid
      grid_consumed_energy_day:
        unit_of_measurement: 'kWh'
        value_template: >
          {% if states("sensor.grid_energy_day") | float > 0 -%}
            {{ states("sensor.grid_energy_day") | float }}
          {%- else -%}
            {{ 0 | float }}
          {%- endif %}
      # calculate energy produced to grid
      grid_sold_energy_day:
        unit_of_measurement: 'kWh'
        value_template: >
          {% if states("sensor.grid_energy_day") | float < 0 -%}
            {{ states("sensor.grid_energy_day") | float * -1 }}
          {%- else -%}
            {{ 0 | float }}
          {%- endif %}
```
