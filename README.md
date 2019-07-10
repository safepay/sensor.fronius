# Fronius Inverter Custom Component for Home Assistant

Returns "Common Inverter Data" from Fronius inverters.

Currently only handles single Inverter devices.

The Default URL called is http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData

If your device has a different id than "1" then pass your device ID as "device_id" as per the configuration.

## Installation
Copy the fronius folder in the custom_components directory into your own custom_components directory in your config directory of Home Assistant.

E.g.:
```
../config/custom_components/fronius/__init__.py
../config/custom_components/fronius/manifest.json
../config/custom_components/fronius/sensor.py
```

Be sure to pull raw data from GitHub:

If you would like to help with development, there is a test verion that can add data from multiple inverters here:
https://github.com/safepay/JSON/blob/master/sensor.py

Just replace the sensor.py in this reppository with this alternate version.
Set "scope: System" in your config to activate.

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
### CONFIGURATION VARIABLES
#### ip_address
(string)(Required)The local IP address of your Fronius Inverter.

#### name
(string)(Optional)The preferred name of your Fronius Inverter. Default: "Fronius"

#### device
(string)(Optional)The Device ID of your Fronius Inverter. Default: 1

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

