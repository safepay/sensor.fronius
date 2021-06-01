[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) [![fronius](https://img.shields.io/github/release/safepay/sensor.fronius.svg)](https://github.com/safepay/sensor.fronius) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)

### Features:
This component simplifies the integration of a Fronius inverter and optional Smart Meter:
* creates up to 12 individual sensors for easy display or use in automations
* converts Wh to kWh
* rounds values to 2 decimal places
* converts yearly and total energy data to kWh or MWh (user-configurable)
* optionally connects to your smart meter (PowerFlow) device for 3 additional sensors
* optionally sums values if you have more than one inverter
* optionally pauses from sunset to sunrise to handle inverter logging going offline at night (always_log: false)

### Minimal Configuration
```
sensor:
- platform: fronius_inverter
    ip_address: LOCAL_IP_FOR_FRONIUS
```

[![Buy me a beer!](https://img.shields.io/badge/Buy%20me%20a%20beer!-%F0%9F%8D%BA-yellow.svg)](https://www.buymeacoffee.com/7PcGoSkb6)
