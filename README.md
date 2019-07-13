[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius)

[![Buy me a beer!](https://img.shields.io/badge/Buy%20me%20a%20beer!-%F0%9F%8D%BA-yellow.svg)](https://www.buymeacoffee.com/7PcGoSkb6)


# Fronius Inverter Sensor for Home Assistant

Returns "Common Inverter Data" from Fronius inverters.

The Default URL called is http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData

If your device has a different id than "1" then pass your device ID as "device_id" as per the configuration.

If you have multiple inverters, set "scope: System" as per the configuration below to return summed values for all inverters.

## Installation
Copy the fronius folder in the custom_components directory into your own custom_components directory in your config directory of Home Assistant.

E.g.:
```
../config/custom_components/fronius/__init__.py
../config/custom_components/fronius/manifest.json
../config/custom_components/fronius/sensor.py
```

Be sure to pull raw data from GitHub or use [HACS](https://custom-components.github.io/hacs/)

## Configuration
```
# Minimal configuration.yaml entry
sensor:
  - platform: fronius
    ip_address: LOCAL_IP_FOR_FRONIUS
```

```
# Example configuration.yaml entry where you can specify the sensors you want:
sensor:
  - platform: fronius
    ip_address: LOCAL_IP_FOR_FRONIUS
    device_id: 1
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
```

```
# Example configuration.yaml entry where you have more than one inverter:
sensor:
  - platform: fronius
    ip_address: LOCAL_IP_FOR_FRONIUS
    scope: System
```
### CONFIGURATION VARIABLES

key | required | type | default | description
--- | -------- | ---- | ------- | -----------
``ip_address`` | yes | string | | The local IP address of your Fronius Inverter.
``name`` | no | string | ``Fronius`` | The preferred name of your Fronius Inverter.
``device_id`` | no | string | ``1`` | The Device ID of your Fronius Inverter.
``scope`` | no | string | ``Device`` | Set to ``System`` if you have multiple inverters. This will return ``ac_power, daily_energy, year_energy`` and, ``total_energy`` only. Case-sensitive.
``scan_interval`` | no | integer | ``300`` | Number of seconds between polls.
``monitored_conditions`` | no | list | All | List of monitored conditions from: ``ac_power, ac_current, ac_voltage, ac_frequency, dc_current, dc_energy, daily_energy, year_energy, total_energy``


