[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius)

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

Be sure to pull raw data from GitHub or use [HACS](https://github.com/custom-components/hacs)

## Configuration
```
# Example configuration.yaml entry
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
#### ip_address
(string)(Required)The local IP address of your Fronius Inverter.

#### name
(string)(Optional)The preferred name of your Fronius Inverter. Default: "Fronius"

#### device
(string)(Optional)The Device ID of your Fronius Inverter. Default: 1

#### scope
(string)(Optional)Set to "System" if you have multiple inverters. This will return ac_power and daily, year and total energy only.
Default: Device
*** Case-sensitive. ***

#### monitored_conditions
(list)(Optional)The list of conditions to monitor. Default - all conditions are monitored.

##### ac_power
The AC Power in W.

##### ac_current
The AC current in A.

##### ac_voltage
The AC voltage in V.

##### ac_frequency
The AC Frequency in Hz.

##### dc_current
The DC Current in A.

##### dc_energy
The DC energy in Wh.

##### daily_energy
The energy in kWh produced that day.

##### year_energy
The energy in kWh produced the last year.

##### total_energy
The energy in kWh produced in the lifetime of the inverter.

