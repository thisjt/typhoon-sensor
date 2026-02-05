# Typhoon Sensor Home Assistant Integration

## Overview
The Typhoon Sensor is a custom Home Assistant integration that provides real-time information about tropical cyclones in the Philippines. It fetches data from the PAGASA Severe Weather Bulletin and calculates the distance of the nearest typhoon's eye from your home coordinates. This integration is designed to help you automate actions, such as managing your solar battery system, in preparation for potential blackouts caused by typhoons.

## Features
- **Real-time Typhoon Data**: Fetches the latest typhoon information from PAGASA.
- **Distance Calculation**: Calculates the distance of the typhoon's eye from your home.
- **Multiple Typhoon Support**: Tracks multiple typhoons and identifies the nearest one.
- **Custom Sensors**:
  - `sensor.typhoon_name`: Name of the nearest typhoon.
  - `sensor.typhoon_last_eye_distance`: Distance of the typhoon's eye from your home.
  - `sensor.typhoon_next_eye_distance`: Predicted distance of the typhoon's eye in the next update.

## Installation
1. Clone this repository into your Home Assistant `custom_components` directory:
   ```
   git clone https://github.com/your-repo/typhoon-sensor.git custom_components/typhoon_sensor
   ```
2. Restart your Home Assistant instance.
3. Add the Typhoon Sensor integration via the Home Assistant UI.

## Configuration
1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for "Typhoon Sensor" and select it.
3. Enter your home coordinates (latitude and longitude) when prompted.

## Example Automation
Here is an example automation to trigger your solar battery system based on the typhoon's proximity:

```yaml
alias: "Prepare for Typhoon"
trigger:
  - platform: numeric_state
    entity_id: sensor.typhoon_last_eye_distance
    below: 100
action:
  - service: switch.turn_on
    target:
      entity_id: switch.solar_battery_charge
mode: single
```

## Dependencies
This integration requires the following Python libraries:
- `requests`
- `beautifulsoup4`
- `haversine`

## License
This project is licensed under the MIT License.