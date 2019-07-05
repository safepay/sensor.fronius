# Home-Assistant-Fronius
A Fronius Inverter component/integration for Home Assistant

Returns "Common Inverter Data" from Fronius inverters

Currently only handles single devices.

The URL called is http://ip_address/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=0&DataCollection=CommonInverterData

## Installation
Copy all the files (except the README) into a fronius folder in your custom_components directory in the config directory of Home Assistant.
E.g. ../config/custom_components/fronius/sensor.py

## Configuration
```
# Example configuration.yaml entry
sensor:
  - platform: fronius
```

```
# Example configuration.yaml entry, limiting the metrics to production only
sensor:
  - platform: fronius
    ip_address: LOCAL_IP_FOR_FRONIUS
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
(string)(Required)The local IP address of your Fronus Inverter.

#### device
(string)(Optional)The Device ID of your Fronus Inverter. Default: 0

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

